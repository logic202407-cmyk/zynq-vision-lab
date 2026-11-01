"""Fault-inject the actual C session configuration parser. Offline DLL only."""
import argparse,binascii,ctypes as C,json
from pathlib import Path

def run(stage):
 lib=C.CDLL(str(stage/'stm32.dll'));cases=[]
 def init():lib.model_init();drain()
 def drain():
  out=bytearray()
  while True:
   b=lib.model_transmit()
   if b<0:return out
   out.append(b)
 def send(s):
  for b in s:lib.model_receive(b,0);lib.model_foreground()
  return drain()
 def wire(s):return (s+'*%04x\n'%binascii.crc_hqx(s.encode(),0xffff)).encode()
 def nonce():return '%08x%08x'%(lib.model_nonce_hi(),lib.model_nonce_lo())
 def bind(n=1,ns=None):return wire('v2b '+(ns or nonce())+' %016x'%n)
 init();reply=send(bind());assert b'V2A ' in reply and lib.c1_session()==1 and lib.model_state()==0;cases.append('correct_bind_ACK_stopped')
 # Existing golden packet for source sequence 5, no hardware inputs.
 import sys
 sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
 from src.pc.vision_measurement import Measurement
 m=Measurement(0,3,1,1,1,5,0,640,480,2,60,80,10,20,50,60,30,40)
 send(m.line());assert lib.c1_sequence()==5
 send(bind());assert lib.c1_sequence()==5;cases.append('duplicate_bind_does_not_rewind')
 send(bind(2));assert lib.c1_session()==2 and lib.c1_accepted()==0
 send(bind(1));assert lib.c1_session()==2;cases.append('older_binding_rejected')
 send(m.line());assert lib.c1_accepted()==0;cases.append('old_measurement_session_rejected')
 for label,data in [('zero',bind(0)),('nonce',bind(3,'ffffffffffffffff')),('crc',bind(3)[:-5]+b'0000\n'),('extra',bind(3)[:-1]+b'x\n'),('uppercase',bind(3).upper())]:
  init();send(data);assert not lib.c1_bound(),label;cases.append('reject_'+label)
 init();lib.model_tx_fill();send(bind());assert not lib.c1_bound();cases.append('no_ACK_space_no_bind')
 init();send(wire('s1 '+nonce()+' 0 arm'));send(bind());assert not lib.c1_bound() and lib.model_state()==1;cases.append('armed_cannot_rebind')
 init();old=bind();lib.model_reboot();send(old);assert not lib.c1_bound();cases.append('MCU_reset_old_nonce_rejected')
 r=dict(verdict='PASS',exit_code=0,count=len(cases),cases=cases,hardware_actions=[])
 (stage/'session-tests.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);run(p.parse_args().stage.absolute())
