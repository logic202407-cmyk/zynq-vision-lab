"""Read-only F03/F04/F06/F07/F08 archive audit; never open hardware or UDP.

Private manifest supplies paths. Public outputs contain hashes and input IDs,
not host paths or camera photographs. Existing collectors/checker/reference
remain unchanged. The independent arithmetic audits recorded statistics; it
does not reconstruct missing raw frames or establish independent board replay.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sim.reference.red_mask import red_binary_mask
from src.pc.frame_evidence import read_frame_bundle

PLAN_SHA = '3301785371b6da99926aa1468c0217bbe2baa50c1e7f593413dcb98e7a084b6a'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def utc(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.utcoffset() is None:
        raise ValueError('timezone required')
    return result


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, indent=2)
        handle.write('\n')


def write_csv(path, rows):
    if not rows:
        raise ValueError('empty table')
    with Path(path).open('x', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def inclusive_overlap(a, b):
    def area(box):
        if (len(box) != 4 or any(type(v) is not int for v in box)
                or not (0 <= box[0] <= box[2] < 640 and 0 <= box[1] <= box[3] < 480)):
            raise ValueError('invalid inclusive image box')
        return (box[2] - box[0] + 1) * (box[3] - box[1] + 1)
    union = area(a) + area(b)
    intersection = max(0, min(a[2], b[2]) + 1 - max(a[0], b[0])) * max(
        0, min(a[3], b[3]) + 1 - max(a[1], b[1]))
    return intersection, union - intersection


def raw_matches(row, index):
    # Sequence alone is reused across restarts and is insufficient.
    return [item['input_id'] for item in index if item['verified']
            and item['frame_seq'] == row['seq']
            and item['input_sha256'] == row['input_sha256']]


def h2_gate(probe, exit_code):
    required = ('elapsed_seconds', 'complete_frames', 'received_payload_bytes',
                'received_datagrams', 'interrupted')
    missing = [key for key in required if key not in probe]
    if missing:
        return {'process_exit_code': exit_code, 'gate': 'UNKNOWN', 'missing_fields': missing}
    failures = []
    if exit_code != 0:
        failures.append('process_exit_nonzero')
    if probe['interrupted'] is not False:
        failures.append('interrupted')
    for key in ('complete_frames', 'received_payload_bytes', 'received_datagrams'):
        if probe[key] <= 0:
            failures.append('zero_' + key)
    if probe['elapsed_seconds'] < 10:
        failures.append('less_than_10_seconds')
    return {'process_exit_code': exit_code, 'gate': 'FAIL' if failures else 'PASS',
            'failure_reasons': failures, 'scope': '10s_real_video_entry_only_not_30s_stability'}


def audit_window(spec, raw_index, protected):
    exact, scene, roi = (load(spec[key]) for key in ('exact', 'scene', 'roi'))
    receipt = load(spec['capture_receipt'])
    if receipt['exit_code'] != spec['capture_exit_code']:
        raise ValueError('capture exit code differs from original receipt')
    _, pilot_meta = read_frame_bundle(Path(spec['pilot_raw']))
    if (pilot_meta['input_sha256'] != roi['input_sha256']
            or sha(spec['pilot_png']) != roi['png_sha256']):
        raise ValueError('ROI source pilot hash mismatch')
    if (len(exact['comparisons']) != 100 or exact['compared'] != 100
            or exact['required_frames'] != 100 or len(scene['comparisons']) != 100):
        raise ValueError('F04 requires the original complete 100-pair archives')
    if spec['capture_exit_code'] != 0 or exact['passed'] is not True or exact['failure_reasons']:
        raise ValueError('original exact gate not passed')
    if (roi['schema'] != 'manual-paper-roi/1' or roi['origin'] != 'manual_unmodified_png'
            or roi['plan_sha256'] != PLAN_SHA or roi['width'] != 640 or roi['height'] != 480
            or utc(roi['frozen_at_utc']) >= utc(exact['started_at_utc'])):
        raise ValueError('ROI provenance or pre-capture timing invalid')
    if scene['exact_report_sha256'] != sha(spec['exact']) or scene['roi_record_sha256'] != sha(spec['roi']):
        raise ValueError('original scene input hash mismatch')
    if scene['checker_sha256'] != sha(ROOT / 'tools/check_board_scene.py'):
        raise ValueError('scene checker source mismatch')
    for name, digest in exact['source_files_sha256'].items():
        if protected.get(name) != digest:
            raise ValueError('exact source mismatch')
    if (exact['expected_mask_version'] != 1 or exact['observed_mask_versions'] != {'1': 100}
            or any(exact[key] != 0 for key in ('mismatch_count', 'sequence_gaps',
                                            'duplicate_sequences', 'mask_version_mismatches'))
            or exact['stop_command_error'] is not None):
        raise ValueError('exact metadata gates invalid')
    rows = []
    for number, (record, archived) in enumerate(zip(exact['comparisons'], scene['comparisons']), 1):
        pl = record['pl']
        if (record['mask_version'] != 1 or record['matches'] is not True
                or record['software'] != pl or pl['frame_complete'] is not True
                or archived['seq'] != record['seq']):
            raise ValueError('pair provenance disagreement')
        if rows and record['seq'] != rows[-1]['seq'] + 1:
            raise ValueError('nonconsecutive archived window')
        valid = pl['target_valid']
        if type(valid) is not bool:
            raise ValueError('valid must be boolean')
        point, box = pl['centroid'], pl['bbox']
        inside, inter, union, iou = False, None, None, None
        if valid:
            if pl['count'] <= 0 or point != [pl['sum_x'] // pl['count'], pl['sum_y'] // pl['count']]:
                raise ValueError('floor-centroid inconsistent with sums')
            bounds = roi['bbox']
            inside = bounds[0] <= point[0] <= bounds[2] and bounds[1] <= point[1] <= bounds[3]
            inter, union = inclusive_overlap(box, bounds)
            iou = inter / union
        matched = valid and inside and inter * 2 >= union
        if (archived['target_valid'] != valid or archived['centroid_in_roi'] != inside
                or archived['scene_matches'] != matched or archived['bbox_iou'] != iou):
            raise ValueError('independent arithmetic differs from original scene rows')
        rows.append({'window_id': spec['id'], 'pair_ordinal': number, 'seq': record['seq'],
                     'input_sha256': record['input_sha256'], 'mask_version': record['mask_version'],
                     'target_valid': valid, 'count': pl['count'], 'sum_x': pl['sum_x'], 'sum_y': pl['sum_y'],
                     'centroid_x': point[0] if point else None, 'centroid_y': point[1] if point else None,
                     **{f'bbox_{key}': box[i] if box else None for i, key in enumerate(('x0','y0','x1','y1'))},
                     'centroid_in_roi': inside, 'intersection': inter, 'union': union, 'iou': iou,
                     'scene_matches': matched, 'saved_raw_ids': '|'.join(raw_matches(record, raw_index))})
    valid_count, semantic = sum(r['target_valid'] for r in rows), sum(r['scene_matches'] for r in rows)
    if valid_count != scene['valid_results'] or semantic != scene['semantic_matches']:
        raise ValueError('original summary differs from per-pair denominator')
    failed = [r['seq'] for r in rows if not r['scene_matches']]
    failures = [r for r in rows if not r['scene_matches']]
    ranges = {}
    for key in ('iou', 'centroid_x', 'centroid_y', 'bbox_x0', 'bbox_y0', 'bbox_x1', 'bbox_y1'):
        values = [r[key] for r in rows if r[key] is not None]
        bad = [r[key] for r in failures if r[key] is not None]
        ranges[key] = {'all': [min(values), max(values)] if values else None,
                       'failed': [min(bad), max(bad)] if bad else None}
    return rows, {'window_id': spec['id'], 'exact_sha256': sha(spec['exact']),
                  'scene_sha256': sha(spec['scene']), 'roi_sha256': sha(spec['roi']),
                  'capture_receipt_sha256': sha(spec['capture_receipt']),
                  'roi_bbox': roi['bbox'], 'roi_frozen_at_utc': roi['frozen_at_utc'],
                  'capture_started_at_utc': exact['started_at_utc'], 'capture_exit_code': spec['capture_exit_code'],
                  'receive_elapsed_seconds': exact['receive_elapsed_seconds'], 'pairs': 100,
                  'valid': valid_count, 'semantic_matches': semantic,
                  'scene_gate_passed': valid_count >= 95 and semantic >= 95,
                  'failed_sequences': failed, 'failed_pair_ordinals': [r['pair_ordinal'] for r in failures],
                  'ranges': ranges, 'raw_covered_pairs': sum(bool(r['saved_raw_ids']) for r in rows),
                  'raw_covered_failed_pairs': sum(bool(r['saved_raw_ids']) for r in failures),
                  'scope': 'independent_archive_arithmetic_not_new_board_or_second_person_reproduction'}


def prepare_blind_review(windows, output):
    """Copy existing unmodified originals privately; never draw or alter them."""
    from PIL import Image
    from src.pc.camera_viewer import rgb565_be_to_image
    from src.pc.vendor_udp import Frame
    output = Path(output).resolve()
    if output.is_relative_to(ROOT) and not output.is_relative_to(ROOT/'private'):
        raise ValueError('blind photographs must remain outside the public repository')
    output.mkdir(parents=True, exist_ok=False)
    reviewer, sealed = output/'reviewer', output/'coordinator-sealed'
    reviewer.mkdir()
    sealed.mkdir()
    records = []
    # Generic letters conceal original run labels; no original ROI/PL fields in reviewer folder.
    for i, spec in enumerate(reversed(windows)):
        label = chr(ord('A') + i)
        raw, meta = read_frame_bundle(Path(spec['pilot_raw']))
        image = Image.open(spec['pilot_png']).convert('RGB')
        expected = rgb565_be_to_image(Frame(raw))
        if image.size != expected.size or image.tobytes() != expected.tobytes():
            raise ValueError('PNG pixels differ from unmodified raw rendering')
        shutil.copyfile(spec['pilot_png'], reviewer/f'{label}.png')
        shutil.copyfile(spec['roi'], sealed/f'{label}-original-roi.json')
        roi = load(spec['roi'])
        records.append({'blind_id':label,'window_id':spec['id'], 'png_sha256':sha(spec['pilot_png']),
                        'input_sha256':meta['input_sha256'],'frame_seq':meta['frame_seq'],
                        'host_saved_at_utc':meta['host_saved_at_utc'],
                        'original_roi':roi,'original_roi_record_sha256':sha(spec['roi']),
                        'png_equals_unmodified_raw_rendering':True})
    with (reviewer/'README.md').open('x',encoding='utf-8') as handle:
        handle.write('# Blind paper-boundary review\n\n'
                     'Independent reviewer: pending; to be assigned by the user.\n'
                     'Use the unmodified 640 x 480 originals A/B. Coordinates are zero-based; '
                     'bbox endpoints are inclusive. Annotate the physical paper boundary, '
                     'not a colour mask. Record [x0,y0,x1,y1], uncertainty in pixels, '
                     'reviewer identifier and UTC; if unclear, mark ungradable.\n\n'
                     'Do not view the sealed folder until both annotations are saved. '
                     'Afterwards compare edge differences and IoU to the sealed originals. '
                     'This review cannot replace historical ROI or rejudge old formal runs.\n')
    write_json(sealed/'mapping.json',records)
    write_json(sealed/'status.json',{'prepared_at_utc':datetime.now(timezone.utc).isoformat(),
                                   'independent_reviewer_completed':False,'status':'prepared_review_pending',
                                   'mapping_sha256':sha(sealed/'mapping.json')})
    return {'status':'prepared_review_pending','independent_reviewer_completed':False,
            'png_raw_pixel_identity_checked':True,'images':len(records),
            'sealed_mapping_sha256':sha(sealed/'mapping.json')}


def components(points):
    # Diagnostic 8-neighbour connectivity only; never select a detector result.
    remaining = set(points)
    groups = []
    while remaining:
        start = min(remaining, key=lambda p: (p[1], p[0]))
        remaining.remove(start)
        group, todo = [], [start]
        while todo:
            x, y = todo.pop()
            group.append((x, y))
            for dx, dy in ((-1,-1), (0,-1), (1,-1), (-1,0), (1,0), (-1,1), (0,1), (1,1)):
                other = (x + dx, y + dy)
                if other in remaining:
                    remaining.remove(other)
                    todo.append(other)
        groups.append(group)
    return groups


def diagnose(spec):
    raw, meta = read_frame_bundle(Path(spec['raw']))
    bounds = spec['diagnostic_bbox']
    inclusive_overlap(bounds, bounds)
    results, point_rows = [], []
    for version in (1, 2):
        mask = red_binary_mask(raw, 640, 480, spatial_filter=version == 2)
        points = [(i % 640, i // 640) for i, value in enumerate(mask) if value]
        inside = [(x, y) for x, y in points if bounds[0] <= x <= bounds[2] and bounds[1] <= y <= bounds[3]]
        outside = set(points) - set(inside)
        box = [min(x for x,y in points), min(y for x,y in points),
               max(x for x,y in points), max(y for x,y in points)] if points else None
        inter, union = inclusive_overlap(box, bounds) if box else (0, 0)
        groups = components(points)
        stats = []
        for idx, group in enumerate(groups, 1):
            group_box = [min(x for x,y in group), min(y for x,y in group),
                         max(x for x,y in group), max(y for x,y in group)]
            touches = [edge for k, edge in enumerate(('left','top','right','bottom'))
                       if box is not None and group_box[k] == box[k]]
            stats.append({'component': idx, 'count': len(group), 'bbox': group_box,
                          'outside_count': sum(p in outside for p in group), 'global_bbox_edges': touches})
            for x, y in sorted(group, key=lambda p: (p[1], p[0])):
                point_rows.append({'input_id': spec['id'], 'input_sha256': meta['input_sha256'],
                                   'mask_version': version, 'component': idx, 'x': x, 'y': y,
                                   'outside_diagnostic_bbox': (x,y) in outside,
                                   'sets_global_bbox_edge': bool(box and (x in (box[0], box[2]) or y in (box[1], box[3])))})
        results.append({'mask_version': version, 'total': len(points), 'inside': len(inside),
                        'outside': len(outside), 'bbox': box, 'iou': inter / union if union else None,
                        'components_8_neighbour': stats})
    return {'input_id': spec['id'], 'input_sha256': meta['input_sha256'], 'frame_seq': meta['frame_seq'],
            'diagnostic_bbox': bounds, 'bbox_role': spec['bbox_role'], 'masks': results,
            'scope': 'offline_snapshot_only_not_formal_window_or_v2_board'}, point_rows


def plots(output, window_rows, summaries, diagnostics, point_rows):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    plt.rcParams.update({'font.size': 9, 'axes.spines.top': False, 'axes.spines.right': False,
                         'svg.fonttype': 'none'})
    def save(fig, name):
        for suffix in ('png', 'pdf', 'svg'):
            path = output / f'{name}.{suffix}'
            fig.savefig(path, dpi=300)
            if suffix == 'svg':
                # Matplotlib emits trailing spaces in multiline path attributes.
                # Normalize text formatting only; preserve all geometry and labels.
                path.write_text('\n'.join(line.rstrip() for line in path.read_text(
                    encoding='utf-8').splitlines()) + '\n', encoding='utf-8')
        plt.close(fig)
    fig, axes = plt.subplots(4, len(summaries), figsize=(12, 10), layout='constrained', squeeze=False)
    for col, summary in enumerate(summaries):
        rows = [r for r in window_rows if r['window_id'] == summary['window_id']]
        x = [r['pair_ordinal'] for r in rows]
        bad = [r for r in rows if not r['scene_matches']]
        axes[0,col].plot(x, [r['iou'] for r in rows], color='#1764ab', linewidth=1)
        axes[0,col].scatter([r['pair_ordinal'] for r in bad], [r['iou'] for r in bad], color='#b3312b', marker='x', s=20)
        axes[0,col].axhline(.5, color='#444444', linestyle='--', label='IoU >= 0.5')
        axes[0,col].set_ylim(0,1)
        axes[0,col].set_title(f"{summary['window_id']}: {summary['semantic_matches']}/100 (requires 95)")
        for key, color in (('centroid_x','#1764ab'), ('centroid_y','#8a4aa5')):
            axes[1,col].plot(x,[r[key] for r in rows], label=key, color=color)
        for axis_row, keys in ((2,('bbox_x0','bbox_x1')), (3,('bbox_y0','bbox_y1'))):
            for key in keys:
                axes[axis_row,col].plot(x,[r[key] for r in rows], label=key, linewidth=1)
            for r in bad:
                axes[axis_row,col].axvline(r['pair_ordinal'],color='#b3312b',alpha=.13)
        for row, label in enumerate(('Inclusive bbox IoU','Floor centroid (px)','BBox x edges (px)','BBox y edges (px)')):
            axes[row,col].set_ylabel(label)
            axes[row,col].set_xlim(1,100)
            axes[row,col].legend(fontsize=8,loc='best')
        axes[3,col].set_xlabel('Pair ordinal; consecutive frames are one window')
    fig.suptitle('F06: original r2/r3 full denominators; both P0 windows failed; no ROI changes')
    save(fig,'formal-window-distributions')
    fig, axes = plt.subplots(len(diagnostics), 2, figsize=(10, 3.5*len(diagnostics)), layout='constrained', squeeze=False)
    for i, item in enumerate(diagnostics):
        for j, mask in enumerate(item['masks']):
            ax = axes[i,j]
            selected = [p for p in point_rows if p['input_id']==item['input_id'] and p['mask_version']==mask['mask_version']]
            for outside,color,marker in ((False,'#1764ab','.'),(True,'#b3312b','x')):
                ps=[p for p in selected if p['outside_diagnostic_bbox']==outside]
                ax.scatter([p['x'] for p in ps],[p['y'] for p in ps],s=7 if outside else 2,c=color,marker=marker,
                           label='outside' if outside else 'inside')
            b=item['diagnostic_bbox']
            ax.add_patch(Rectangle((b[0]-.5,b[1]-.5),b[2]-b[0]+1,b[3]-b[1]+1,fill=False,edgecolor='#333333',linestyle='--'))
            ax.set(xlim=(0,639),ylim=(479,0),xlabel='x (px)',ylabel='y (px)',aspect='equal',
                   title=f"{item['input_id']} v{mask['mask_version']}: outside {mask['outside']}/{mask['total']}")
            ax.legend(fontsize=7,loc='lower left')
    fig.suptitle('F08: frozen masks on pilot snapshots; dashed boxes are diagnostic; v2 is offline only')
    save(fig,'pilot-mask-point-contributions')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path,help='New directory for sanitized statistics only')
    parser.add_argument('--blind-output',type=Path,help='Optional NEW private blind review directory')
    args=parser.parse_args(argv)
    manifest=load(args.manifest)
    if args.output.exists():
        parser.error('use a new output directory; no overwrite')
    protected=load(ROOT/'report/experiments/2026-10-04-v1-scene-validation.json')['protected_files_sha256']
    if any(sha(ROOT/name)!=digest for name,digest in protected.items()):
        parser.error('protected byte hash changed')
    original_files = {Path(manifest['zero_probe'])}
    for spec in manifest['windows']:
        original_files.update(Path(spec[key]) for key in ('exact','scene','roi','capture_receipt','pilot_raw','pilot_png'))
    for spec in manifest['diagnostics']:
        original_files.add(Path(spec['raw']))
    for root in manifest['raw_roots']:
        for path in Path(root['path']).rglob('*.rgb565'):
            original_files.add(path)
            sidecar = path.with_suffix(path.suffix+'.json')
            if sidecar.exists():
                original_files.add(sidecar)
    before = {path:sha(path) for path in original_files}
    raw_index=[]
    for root in manifest['raw_roots']:
        for path in sorted(Path(root['path']).rglob('*.rgb565')):
            item={'input_id':root['id']+'/'+path.relative_to(root['path']).as_posix(),
                  'verified':False,'frame_seq':None,'input_sha256':None,
                  'scope':'unknown','sidecar_sha256':None,'host_saved_at_utc':None}
            try:
                _,meta=read_frame_bundle(path)
                if type(meta.get('frame_seq')) is not int or not 0 < meta['frame_seq'] < 0xffffffff:
                    raise ValueError('missing/invalid snapshot sequence')
                utc(meta['host_saved_at_utc'])
                item.update(verified=True,frame_seq=meta['frame_seq'],input_sha256=meta['input_sha256'],
                            scope=meta['scope'],sidecar_sha256=sha(str(path)+'.json'),host_saved_at_utc=meta['host_saved_at_utc'])
            except (OSError,ValueError,KeyError,TypeError):
                item['error']='raw_bundle_missing_or_invalid; private path withheld'
            raw_index.append(item)
    rows,summaries=[],[]
    for spec in manifest['windows']:
        window,summary=audit_window(spec,raw_index,protected)
        rows.extend(window)
        summaries.append(summary)
    diag,points=[],[]
    for spec in manifest['diagnostics']:
        result,new_points=diagnose(spec)
        diag.append(result)
        points.extend(new_points)
    probe=load(manifest['zero_probe'])
    negative={'probe_sha256':sha(manifest['zero_probe']), 'metrics':probe,
              'evaluation':h2_gate(probe,manifest['zero_probe_exit_code']),
              'expected_gate':'FAIL', 'scope':'existing_zero_frame_negative_control_no_network_execution'}
    if negative['evaluation']['gate']!='FAIL':
        raise ValueError('negative control unexpectedly did not fail')
    blind = prepare_blind_review(manifest['windows'],args.blind_output) if args.blind_output else {'status':'not_prepared'}
    args.output.mkdir(parents=True,exist_ok=False)
    write_json(args.output/'raw-index.json',raw_index)
    write_csv(args.output/'formal-pairs.csv',rows)
    write_csv(args.output/'formal-raw-coverage.csv',[{'window_id':r['window_id'],'pair_ordinal':r['pair_ordinal'],
              'seq':r['seq'],'input_sha256':r['input_sha256'],'saved_raw_ids':r['saved_raw_ids'],
              'can_reanalyse_pixels':bool(r['saved_raw_ids']), 'semantic_failure':not r['scene_matches']} for r in rows])
    write_json(args.output/'window-audit.json',summaries)
    write_json(args.output/'zero-frame-negative-control.json',negative)
    write_json(args.output/'pilot-components.json',diag)
    write_json(args.output/'blind-review-status.json',blind)
    write_csv(args.output/'pilot-points.csv',points)
    plots(args.output,rows,summaries,diag,points)
    if any(sha(path)!=digest for path,digest in before.items()):
        raise ValueError('original archive changed during audit')
    write_json(args.output/'audit-provenance.json',{'schema':'fpga-archive-audit/1',
               'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
               'source_baseline':manifest['source_baseline'],'captain_task_commit':manifest['captain_task_commit'],
               'audit_script_sha256':sha(__file__), 'protected_files_sha256':protected,
               'scope':'offline_archival_not_board_replay', 'windows':len(summaries),'pairs':len(rows),
               'raw_bundles_scanned':len(raw_index),'raw_bundles_verified':sum(i['verified'] for i in raw_index),
               'snapshot_diagnostics':len(diag),'raw_search_scope':'declared existing run roots only; not the entire disk',
               'original_archive_files_checked':len(before),'original_archives_unchanged_after_audit':True,
               'limits':['No saved formal raw bytes inferred from pilot','No second-person ROI review',
                         'Host save times are not sensor exposure timestamps','No v2 hardware test']})
    print(json.dumps({'pairs':len(rows),'semantic_matches':[s['semantic_matches'] for s in summaries],
                      'formal_raw_coverage':[s['raw_covered_pairs'] for s in summaries],
                      'raw_bundles':len(raw_index),'zero_frame_gate':negative['evaluation']['gate']}))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
