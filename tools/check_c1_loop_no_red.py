"""Supplemental coupled case: actual PL no-red result must revoke tracking."""
import argparse,json,hashlib,traceback,time
from pathlib import Path
from check_c1_loop import Loop

def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);s=p.parse_args().stage.absolute()
 c=Loop(s);result={};started=time.monotonic()
 try:
  c.vision(reset=0);c.advance(2);c.vision();c.sync();c.bind(nonce=0);c.arm()
  c.pump=True;c.next_frame=c.us;c.advance(40000)
  c.put('loop_controls',3,1);c.advance(2);c.put('loop_controls',2,1)
  c.until(lambda:c.lib.model_reg(0x40000820)==17,250000)
  c.put('loop_controls',6,1) # confirmed scene, but rendered primary image is all black
  c.until(lambda:c.lib.model_reg(0x40000820)==0,400000)
  assert c.lstatus()&2
  packets=[bytes.fromhex(x[3:].strip()) for x in c.lines if x.startswith('v2 ')]
  assert any(p[5]&2 and int.from_bytes(p[28:32],'big')==64 for p in packets)
  assert any(not(p[5]&2) and int.from_bytes(p[28:32],'big')==0 for p in packets)
  count=sum(' pan ' in x or ' tlt ' in x for x in c.lines)
  c.put('loop_controls',2,1);c.advance(180000)
  assert c.lib.model_reg(0x40000820)==0 and count==sum(' pan ' in x or ' tlt ' in x for x in c.lines)
  result=dict(verdict='PASS',case='primary_no_red_while_OpenMV_valid',exit_code=0,
    wall_seconds=time.monotonic()-started,simulated_us=c.us,hardware_actions=[],
    harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
 except Exception:
  result=dict(verdict='FAIL',exit_code=1,error=traceback.format_exc());raise
 finally:
  (s/'result-no-red.json').write_text(json.dumps(result,indent=2))
  (s/'wire-no-red.json').write_text(json.dumps(dict(to_mcu=c.lines,from_mcu=bytes(c.from_mcu).decode(errors='replace'),trace=c.trace,plant=c.plant),indent=2))
  c.close()
 print(json.dumps(result,indent=2))

if __name__=='__main__':main()
