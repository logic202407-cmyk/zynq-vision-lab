"""Adversarial replay with repeated/fresh test epochs; no claim of random uniqueness."""
import argparse,json
from pathlib import Path
from check_motion_cosim import build,Coupled
p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--fresh',action='store_true');p.add_argument('--built',action='store_true');a=p.parse_args();s=a.stage.absolute()
if not a.built:build(s)
c=Coupled(s)
try:
 c.sync();old=next(x+b'\n' for x in bytes(c.from_mcu).splitlines() if x.startswith(b'S1SYNC '))
 c.setbit(0,0);c.advance(10);c.setbit(0,1);c.advance(200)
 c.disconnect=True;c.hold=True;c.until(lambda:bool(c.status&16))
 if a.fresh:
  c.controls=(c.controls&~(((1<<128)-1)<<23))|(0x88776655<<23);c.drive()
 c.pulse(1);c.until(lambda:c.state==2)
 c.replay.extend(b'\n'+old);c.advance(20000)
 rejected=c.state!=3
 result={'case':'fresh_epoch' if a.fresh else 'repeated_epoch','expected':'old sync must not be accepted','observed_state':c.state,'replay_rejected':rejected,'exit_code':0 if rejected else 1,'scope':'test fixture replay; not hardware entropy','requests':c.lines,'replayed':old.decode(),'source':'unchanged B2 RTL and actual C-generated initial S1SYNC'}
 (s/('epoch-fresh.json' if a.fresh else 'epoch-repeat.json')).write_text(json.dumps(result,indent=2));print(json.dumps(result));code=result['exit_code']
finally:c.close()
raise SystemExit(code)
