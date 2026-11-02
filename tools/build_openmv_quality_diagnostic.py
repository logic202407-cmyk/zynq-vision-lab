"""Build a finite standalone RAM image diagnostic; does not access a device."""
import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PROTO=ROOT/'src/prototype/skystar_openmv'


def generate(seconds=30, bench_threshold=None):
    if not 1<=seconds<=90:
        raise ValueError('Finite diagnostic duration must be 1..90 seconds')
    if bench_threshold is not None and (len(bench_threshold)!=6 or
            not 0<=bench_threshold[0]<=bench_threshold[1]<=100 or
            not -128<=bench_threshold[2]<=bench_threshold[3]<=127 or
            not -128<=bench_threshold[4]<=bench_threshold[5]<=127):
        raise ValueError('Invalid LAB threshold')
    config={}
    for node in ast.parse((PROTO/'openmv_main.py').read_text(encoding='utf-8')).body:
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
            if node.targets[0].id in ('red_threshold','PIXELS_THRESHOLD','AREA_THRESHOLD','MIN_BLOB_AREA','FRAME_BORDER','STABLE_FRAMES'):
                config[node.targets[0].id]=ast.literal_eval(node.value)
    profiles=[('repository_default',config['red_threshold'])]
    if bench_threshold is not None:profiles.append(('explicit_bench_reference',tuple(bench_threshold)))
    policy=(PROTO/'red_target_policy.py').read_text(encoding='utf-8')
    body='''
import sensor
import time
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QQVGA)
sensor.skip_frames(time=2000)
sensor.set_auto_whitebal(False)
sensor.set_auto_gain(False)
PROFILES = PROFILES_LITERAL
CONFIG = CONFIG_LITERAL
policies = [RedTargetPolicy(CONFIG['MIN_BLOB_AREA'], CONFIG['FRAME_BORDER'], CONFIG['STABLE_FRAMES']) for _ in PROFILES]
for name in ('get_hmirror', 'get_vflip', 'get_transpose'):
    getter = getattr(sensor, name, None)
    print('CAMERA_GEOMETRY', name, getter() if callable(getter) else 'UNKNOWN')
print('QUALITY_CONFIG', PROFILES, CONFIG, 'NO_UART_NO_FLASH_NO_ACTUATORS')
started = time.ticks_ms()
last = started
while time.ticks_diff(time.ticks_ms(), started) < DURATION_MS:
    image = sensor.snapshot()
    results = []
    # Both detections run before drawing so overlay pixels never contaminate the second profile.
    for index, item in enumerate(PROFILES):
        blobs = image.find_blobs([item[1]], pixels_threshold=CONFIG['PIXELS_THRESHOLD'], area_threshold=CONFIG['AREA_THRESHOLD'], merge=False)
        selected = policies[index].choose(blobs, 160, 120)
        candidates = sum(1 for b in blobs if blob_value(b, 'area') >= CONFIG['MIN_BLOB_AREA'])
        results.append((selected, candidates, target_offsets(selected)))
    chosen = results[-1][0]
    if chosen is not None:
        image.draw_rectangle(blob_value(chosen, 'rect'), color=(0, 255, 0))
        image.draw_cross((blob_value(chosen, 'cx'), blob_value(chosen, 'cy')), color=(0, 255, 0))
    image.draw_string((2, 2), PROFILES[-1][0], color=(255, 255, 0))
    image.draw_string((2, 14), policies[-1].reason, color=(255, 255, 0))
    now = time.ticks_ms()
    if time.ticks_diff(now, last) >= 500:
        for index, item in enumerate(PROFILES):
            print('QUALITY_IMAGE_ONLY', item[0], policies[index].reason, results[index][1], results[index][2])
        last = now
for name in ('get_hmirror', 'get_vflip', 'get_transpose'):
    getter = getattr(sensor, name, None)
    print('CAMERA_GEOMETRY_END', name, getter() if callable(getter) else 'UNKNOWN')
print('QUALITY_IMAGE_DIAGNOSTIC_DONE')
'''
    body=body.replace('PROFILES_LITERAL',repr(profiles)).replace('CONFIG_LITERAL',repr(config)).replace('DURATION_MS',str(seconds*1000))
    return '# Finite image-only RAM diagnostic. No UART, actuator or filesystem writes.\n'+policy+'\n'+body


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--seconds',type=int,default=30)
    parser.add_argument('--bench-threshold',help='Six explicit LAB integers, comma-separated; never changes repository default')
    args=parser.parse_args()
    threshold=tuple(int(x) for x in args.bench_threshold.split(',')) if args.bench_threshold else None
    script=generate(args.seconds,threshold);compile(script,str(args.output),'exec')
    args.output.write_bytes(script.encode('utf-8'))
    metadata=dict(scope='Generation only; finite image-only RAM script, not uploaded or executed by this tool',
        seconds=args.seconds,bench_threshold=threshold,
        script_sha256=hashlib.sha256(script.encode('utf-8')).hexdigest(),
        source_sha256={p.resolve().relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in (PROTO/'red_target_policy.py',PROTO/'openmv_main.py',Path(__file__))})
    args.output.with_suffix('.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print('FINITE_IMAGE_DIAGNOSTIC_BUILT',args.output)
