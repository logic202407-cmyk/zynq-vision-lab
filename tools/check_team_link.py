"""Opt-in AUTO RTL coupled to actual F407 C; no physical I/O."""
import argparse,json,time,traceback
from pathlib import Path
from check_c1_link import build,Link
p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True)
p.add_argument('--built',action='store_true');p.add_argument('--case',choices=['normal','vision_loss','ack_target','repeat_auto'],default='normal');a=p.parse_args()
if not a.built:build(a.stage,team=True)
c=Link(a.stage);passed=[];result={}
try:
    c.vision(reset=0);c.put('camera_frame',0,1);c.advance(2);c.vision();c.sync();c.bind(nonce=0)
    passed.append('query_and_observation_bind')
    c.arm();assert c.lib.model_reg(0x40000820)==0
    old=c.accepts;c.command(3,0);c.until(lambda:c.accepts>old)
    assert c.state==4 and c.lib.model_state()==3
    passed.append('FPGA_serializes_AUTO_and_accepts_correlated_real_C_ACK')
    for i in range(12):
        c.lib.model_vision(12,8,1);c.advance(25000)
        assert c.lib.model_state()==3 and not c.status&32
        assert c.lib.model_reg(0x40000820)==17 and c.lib.model_reg(0x40021018)==4
    assert any(' hb*' in line for line in c.lines)
    assert c.lib.model_pan()!=1500 and c.lib.model_tilt()!=1500
    passed.append('AUTO_heartbeat_accepts_changing_in_range_targets_and_PWM_snapshot')
    if a.case=='normal':
        c.stop();passed.append('FPGA_STOP_disables_PWM_and_PE2')
    elif a.case=='vision_loss':
        c.advance(300000);assert c.lib.model_state()==4
        passed.append('vision_loss_faults_and_FPGA_confirms_STOP')
    elif a.case=='ack_target':
        c.mutate='target'
        for i in range(12):c.lib.model_vision(12,8,1);c.advance(25000)
        assert c.status&32
        passed.append('CRC_valid_AUTO_heartbeat_target_CCR_mismatch_rejected')
    else:
        c.until(lambda:c.state==4);c.command(3,0);c.advance(100000);assert c.status&32
        passed.append('second_AUTO_requires_STOP_and_new_authorization')
    assert c.lib.model_reg(0x40021018)==1<<18 and c.lib.model_reg(0x40000820)==0
    assert c.status&64
    result={'verdict':'PASS','cases':passed,'simulated_us':c.us,'scope':'XSim plus actual C register model only'}
except Exception:
    result={'verdict':'FAIL','cases':passed,'error':traceback.format_exc(),'simulated_us':c.us}
    raise
finally:
    (a.stage/('team-result-'+a.case+'.json')).write_text(json.dumps(result,indent=2))
    (a.stage/('team-wire-'+a.case+'.json')).write_text(json.dumps({'to_mcu':c.lines,'from_mcu':bytes(c.from_mcu).decode(errors='replace')},indent=2))
    c.close()
print(json.dumps(result,indent=2))
