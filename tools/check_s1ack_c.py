"""Exercise the compiled S1ACK1 candidate's actual ISR/parser/guardian/driver."""
import argparse,ctypes as C,json,binascii
from pathlib import Path

def wire(s):return (s+'*%04x\n'%binascii.crc_hqx(s.encode(),0xffff)).encode()
def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);a=p.parse_args();lib=C.CDLL(str(a.stage.absolute()/'stm32.dll'))
 lib.model_reg.argtypes=[C.c_uint];lib.model_reg.restype=C.c_uint
 passed=[];out=bytearray();ticks=0
 def drain():
  while True:
   b=lib.model_transmit()
   if b<0:break
   out.append(b)
 def reset():
  nonlocal ticks
  lib.model_init();ticks=0;out.clear();drain();out.clear()
 def send(data):
  for b in data:lib.model_receive(b,0);lib.model_foreground();drain()
 def nonce():return '%08x%08x'%(lib.model_nonce_hi(),lib.model_nonce_lo())
 def cmd(seq,payload,n=None):return wire('s1 %s %d %s'%(n or nonce(),seq,payload))
 def arm():send(cmd(0,'arm'));assert lib.model_state()==1 and lib.model_reg(0x40000820)==0
 def pan():send(cmd(1,'pan 1550'));assert lib.model_pan()==1550 and lib.model_reg(0x40000820)==17
 def off():
  assert lib.model_reg(0x40000820)==0
  assert (lib.model_reg(0x40020c00)>>24)&15==5
  assert lib.model_reg(0x40020c18)&0x30000000==0x30000000
 def step(n,foreground=True):
  for _ in range(n):
   lib.model_tick()
   if foreground:lib.model_foreground();drain()
 def ack(op,result='ACCEPT'):
  matches=[x for x in out.decode().splitlines() if x.startswith('S1ACK ') and (' '+op+' '+result+' ') in x]
  assert matches,(op,result,out)
  b,crc=matches[-1].split('*');assert int(crc,16)==binascii.crc_hqx(b.encode(),0xffff)
  return b.split()
 def case(name,fn):
  reset();fn();passed.append(name)
 def query():
  send(wire('s1q '+'1'*32+' st'));assert ('S1SYNC '+'1'*32+' S1ACK1 '+nonce()) in out.decode();off()
 case('query_crc_nonce',query)
 case('arm_off',arm)
 def axes():
  arm();pan();assert lib.model_tilt()==1500
  send(cmd(2,'tlt 1540'));assert lib.model_pan()==1550 and lib.model_tilt()==1540
  send(cmd(3,'pan 1500'));assert lib.model_tilt()==1540
  send(cmd(4,'tlt 1500'));assert lib.model_pan()==1500 and lib.model_tilt()==1500
  send(cmd(5,'home'));assert ack('home')[14]=='3'
 case('axis_targets_dual_enable_and_home',axes)
 def repeat():
  arm();pan();step(20);live=lib.model_live();send(cmd(1,'pan 1550'));assert ack('pan','REJECT')[11]=='sequence';assert lib.model_live()==live
  send(cmd(0,'tlt 1550'));assert ack('tlt','REJECT')[11]=='sequence';assert lib.model_live()==live
 case('duplicate_and_reverse_no_renewal',repeat)
 def session():
  arm();pan();live=lib.model_live();send(cmd(2,'tlt 1550','ffffffffffffffff'));assert ack('tlt','REJECT')[11]=='session';assert lib.model_live()==live
 case('wrong_nonce',session)
 def badcrc():
  arm();pan();w=bytearray(cmd(2,'tlt 1540'));w[-2]=ord('0') if w[-2]!=ord('0') else ord('1');out.clear();send(w);off();assert lib.model_state()==4 and 'S1ACK ' not in out.decode()
 case('request_crc_fault_no_fabricated_ack',badcrc)
 for payload in ['pan 1299','tlt 1701','tilt 1500','pan -1','pan 1500 extra']:
  def invalid(payload=payload):
   arm();pan();send(cmd(2,payload));off();assert lib.model_state()==4
  case('invalid_'+payload,invalid)
 def boundaries():
  arm();send(cmd(1,'pan 1300'));send(cmd(2,'tlt 1700'));assert lib.model_pan()==1300 and lib.model_tilt()==1700
 case('software_boundaries_only',boundaries)
 def naked():
  arm();pan();send(b'pan 1500\n');off();assert lib.model_state()==4
 case('legacy_motion_no_bypass',naked)
 def heartbeat():
  arm();step(300);send(cmd(1,'hb'));step(300);assert lib.model_state()==1;off();assert ack('hb')[14]=='0'
 case('heartbeat_renewal_without_output_enable',heartbeat)
 def lease():
  arm();pan();step(499,False);assert lib.model_reg(0x40000820)==17
  step(1,False);off();lib.model_foreground();assert lib.model_state()==4
  old=nonce();send(cmd(2,'hb'));off();send(b'stop\n');assert lib.model_state()==4 and nonce()==old
  send(cmd(0,'arm'));assert lib.model_state()==1;off();send(cmd(1,'tlt 1540'));assert lib.model_reg(0x40000820)==17
 case('isr_500ms_fault_latch_explicit_rearm',lease)
 def partial():
  arm();pan();send(b's1 partial');step(200);off();assert lib.model_state()==4
 case('partial_200ms',partial)
 def overflow():
  arm();pan();send(b'x'*100+b'\n');off();assert lib.model_state()==4
 case('line_overflow',overflow)
 def uart():
  arm();pan();lib.model_receive(0,1);off();lib.model_foreground();assert lib.model_state()==4
 case('uart_framing_fault',uart)
 def saturation():
  arm();pan();lib.model_tx_fill()
  for b in cmd(2,'tlt 1540'):lib.model_receive(b,0);lib.model_foreground()
  off();assert lib.model_state()==4 and lib.model_tilt()==1500
 case('tx_queue_admission_fails_off',saturation)
 def qstop():
  arm();pan();send(wire('s1q '+'2'*32+' stop'));off();a=ack('stop');assert a[1]=='Q' and a[2]=='2'*32 and a[14]=='0'
 case('correlated_stop_register_off',qstop)
 def reset_test():
  arm();pan();old=nonce();lib.model_reboot();assert nonce()!=old;off();assert lib.model_state()==0
 case('mcu_reboot_fresh_fixture_nonce_off',reset_test)
 def querymotion():
  arm();pan();send(wire('s1q '+'3'*32+' pan 1550'));off();assert lib.model_state()==4
 case('query_namespace_cannot_move',querymotion)
 def maxseq():
  arm();send(cmd(4294967295,'pan 1550'));assert lib.model_pan()==1550
  live=lib.model_live();send(cmd(0,'hb'));assert ack('hb','REJECT')[11]=='sequence' and lib.model_live()==live
 case('sequence_max_and_wrap_rejected',maxseq)
 def queued():
  arm();pan()
  for b in cmd(2,'tlt 1540'):lib.model_receive(b,0)
  step(200,False);lib.model_foreground();off();assert lib.model_state()==4
 case('queued_stale_200ms',queued)
 def hbdup():
  arm();send(cmd(1,'hb'));step(100);live=lib.model_live();send(cmd(1,'hb'))
  assert lib.model_live()==live;off();assert ack('hb','REJECT')[11]=='sequence'
 case('duplicate_heartbeat_no_renewal',hbdup)
 def leading_zero_sequence():
  send(wire('s1 '+nonce()+' 00000000000000000000 arm'))
  assert lib.model_state()==1 and ack('arm')[3]=='0'
  send(wire('s1 '+nonce()+' 00000000000000000001 pan 1550'))
  assert lib.model_pan()==1550 and ack('pan')[3]=='1'
 case('legacy_leading_zero_sequence_preserved',leading_zero_sequence)
 result={'pass'  :'S1ACK1_C_PASS','count':len(passed),'cases':passed,'exit_code':0,'scope':'actual C + register model, not RTL or hardware'}
 (a.stage/'c-tests.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
