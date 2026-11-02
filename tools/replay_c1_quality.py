"""Counterfactual replay through actual C1 quality code. No device access."""
import argparse
from collections import Counter
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
FW=ROOT/'src/prototype/skystar_openmv/stm32_skystar_tracking/User'


def replay(input_path,stage,width,height):
    if not 3<=width<=65535 or not 3<=height<=65535:
        raise ValueError('Explicit capture resolution required')
    stage=stage.absolute();stage.mkdir(parents=True,exist_ok=False)
    env=os.environ.copy();env.update(TEMP=str(stage),TMP=str(stage))
    command=[os.environ.get('CC','D:/Dev-Cpp/MinGW64/bin/gcc.exe'),'-shared','-std=c99','-Wall','-Wextra','-Werror','-O2',
             '-I'+str(FW),str(ROOT/'sim/c1/quality_replay.c'),'-o',str(stage/'quality.dll')]
    result=subprocess.run(command,cwd=stage,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (stage/'compile.txt').write_bytes(result.stdout)
    if result.returncode:raise RuntimeError(result.stdout.decode('utf-8','replace'))
    library=ctypes.CDLL(str(stage/'quality.dll'))
    classify=library.replay_quality;classify.argtypes=[ctypes.c_uint]*10;classify.restype=ctypes.c_uint
    data=json.loads(input_path.read_text(encoding='utf-8'));reasons=Counter();counts=[]
    rejected=[]
    for index,sample in enumerate(data['samples']):
        reason=int(classify(sample['count'],sample['flags'],width,height,*sample['bbox'],*sample['centroid']))
        reasons[reason]+=1;counts.append(sample['count'])
        if reason:rejected.append(dict(index=index,reason=reason,count=sample['count'],bbox=sample['bbox']))
    names={0:'usable',1:'incomplete',2:'sparse',3:'edge',4:'geometry'}
    report=dict(scope='Offline counterfactual: candidate not deployed; not a physical tracking acceptance',
        command=command,compile_exit_code=result.returncode,width=width,height=height,
        samples=len(counts),count_range=[min(counts),max(counts)],
        reasons={names[key]:value for key,value in sorted(reasons.items())},
        rejected=rejected,input_sha256=hashlib.sha256(input_path.read_bytes()).hexdigest(),
        source_sha256={p.resolve().relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in (FW/'c1_quality.h',ROOT/'sim/c1/quality_replay.c',Path(__file__))})
    (stage/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True);p.add_argument('--stage',type=Path,required=True)
    p.add_argument('--width',type=int,required=True);p.add_argument('--height',type=int,required=True)
    a=p.parse_args();r=replay(a.input,a.stage,a.width,a.height)
    print(json.dumps({k:v for k,v in r.items() if k in ('scope','samples','count_range','reasons','compile_exit_code')},indent=2))
