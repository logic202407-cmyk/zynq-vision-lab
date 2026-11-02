"""Offline camera-centering calibration analysis. No device access or commands.

Fits local pixel-error response to software PWM targets. A fit is neither a
mechanical angle measurement nor proof of a PWM waveform. Never edits RTL signs.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path


def fit_axis(samples, axis):
    if axis not in ('pan', 'tlt'):
        raise ValueError('Protocol axis must be pan or tlt')
    selected=[s for s in samples if s['axis']==axis]
    pulse=axis+'_us';other='tlt_us' if axis=='pan' else 'pan_us'
    response='dx' if axis=='pan' else 'dy'
    cross='dy' if axis=='pan' else 'dx'
    if not selected or any(not math.isfinite(float(s[k])) for s in selected
                           for k in (pulse,other,response,cross)):
        raise ValueError('Missing or nonfinite response samples')
    counts=Counter(s[pulse] for s in selected)
    if len(counts)<3 or min(counts.values())<2:
        raise ValueError('At least three distinct targets, each repeated, required')
    if len({s[other] for s in selected})!=1:
        raise ValueError('Other axis must remain fixed during identification')
    x=[float(s[pulse]) for s in selected];mean=sum(x)/len(x)
    denominator=sum((p-mean)**2 for p in x)
    def regression(key):
        y=[float(s[key]) for s in selected];average=sum(y)/len(y)
        slope=sum((p-mean)*(v-average) for p,v in zip(x,y))/denominator
        residual=max(abs(v-(average+slope*(p-mean))) for p,v in zip(x,y))
        return slope,residual
    slope,residual=regression(response);coupling,_=regression(cross)
    if slope==0:
        raise ValueError('No observable primary response; sign cannot be identified')
    return dict(axis=axis, pixels_per_us=slope,
                proposed_control_sign=-1 if slope>0 else 1,
                cross_pixels_per_us=coupling,cross_ratio=abs(coupling/slope),
                max_residual_px=residual,sample_count=len(selected),
                evidence_kind=sorted({s['evidence_kind'] for s in selected}),
                scope='Local response fit only; not angle, limit, stability or waveform certification')


def assess(record):
    blockers=[];fits={}
    if record.get('gimbal_id')!=0:blockers.append('ONLY_GIMBAL1_PREPARATION_ALLOWED')
    if not record.get('same_target_observed'):blockers.append('SAME_TARGET_NOT_OBSERVED')
    if not record.get('camera_geometry_verified'):blockers.append('CAMERA_GEOMETRY_UNKNOWN')
    if not record.get('independent_pwm_waveform_verified'):blockers.append('PWM_WAVEFORM_UNMEASURED')
    if not record.get('mechanical_window_verified'):blockers.append('MECHANICAL_WINDOW_UNVERIFIED')
    if not record.get('epoch_provider_certified'):blockers.append('EPOCH_HARDWARE_BLOCKER')
    policy=record.get('response_acceptance_policy')
    if not policy or not all(isinstance(policy.get(k),(int,float)) and
          math.isfinite(policy[k]) and policy[k]>=0
          for k in ('min_abs_slope','max_cross_ratio','max_residual_px')):
        blockers.append('RESPONSE_ACCEPTANCE_POLICY_UNSET');policy=None
    for axis in ('pan','tlt'):
        try:
            result=fit_axis(record.get('samples',[]),axis);fits[axis]=result
            if result['evidence_kind']!=['measured']:
                blockers.append(axis.upper()+'_SIMULATION_IS_NOT_CALIBRATION')
            if policy and (abs(result['pixels_per_us'])<policy['min_abs_slope'] or
                           result['cross_ratio']>policy['max_cross_ratio'] or
                           result['max_residual_px']>policy['max_residual_px']):
                blockers.append(axis.upper()+'_RESPONSE_POLICY_FAILED')
        except (ValueError,KeyError,TypeError) as error:
            blockers.append(axis.upper()+'_RESPONSE_MISSING_OR_INVALID: '+str(error))
    return dict(status='BLOCKED' if blockers else 'EVIDENCE_REVIEW_REQUIRED',
                motion_authorized=False,blockers=blockers,fits=fits,
                note='Analysis never grants permission, configures hardware or writes controller parameters')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=assess(json.loads(args.input.read_text(encoding='utf-8')))
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(result['status']);raise SystemExit(2 if result['blockers'] else 0)
