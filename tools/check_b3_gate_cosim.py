"""Actual B2 routed netlist + actual STM32 C. Wall budget never means PASS."""
import argparse,subprocess,shutil,time,json,hashlib
from pathlib import Path
from check_motion_cosim import build,Coupled,ROOT,VB
p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--netlist',type=Path,required=True);p.add_argument('--seconds',type=int,default=600);p.add_argument('--fast',action='store_true');a=p.parse_args();s=a.stage.absolute()
build(s)
shutil.copyfile(a.netlist,s/'motion_func.v');shutil.copyfile(ROOT/'sim/cosim/b3_gate_bridge_tb.v',s/'gate_tb.v');shutil.copyfile(VB.parent/'data/verilog/src/glbl.v',s/'glbl.v')
receipt={'netlist_sha256':hashlib.sha256(a.netlist.read_bytes()).hexdigest(),'scope':'routed functional netlist + real STM32 C; not RTL','steps':[]}
for name,cmd in [('gate-xvlog',[str(VB/'xvlog.bat'),'motion_func.v','gate_tb.v','glbl.v']),('gate-xelab',[str(VB/'xelab.bat'),'b3_gate_bridge_tb','glbl','-L','unisims_ver','-debug','all','-dll','-s','coupled'])]:
 if name=='gate-xelab' and a.fast:cmd=[x for x in cmd if x not in ['-debug','all']]+['-debug','off','--O3']
 q=subprocess.run(cmd,cwd=s,capture_output=True,timeout=300);(s/(name+'.log')).write_bytes(q.stdout+q.stderr);receipt['steps'].append({'command':cmd,'exit_code':q.returncode});assert q.returncode==0
start=time.monotonic();c=Coupled(s);original=c.advance
class Budget(Exception):pass
def advance(n):
 for k in range(0,n,100):
  original(min(100,n-k))
  if c.us%1000<100:
   (s/'progress.json').write_text(json.dumps({'simulated_us':c.us,'wall_seconds':time.monotonic()-start,'state':c.state,'requests':c.lines}))
   print('GATE_PROGRESS',c.us,c.state,len(c.lines),round(time.monotonic()-start,1),flush=True)
  if time.monotonic()-start>a.seconds:raise Budget()
c.advance=advance
code=0
try:
 c.advance(200);assert not c.to_mcu
 c.until(lambda:bool(c.status&16))
 c.pulse(1);c.until(lambda:c.state==3)
 c.arm()
 for ax,val in [(0,1550),(1,1550),(0,1500),(1,1500),(0,1540),(1,1530),(2,1500)]:c.move(ax,val)
 old=c.accepts;c.until(lambda:c.accepts>old);c.stop()
 expected=json.loads((ROOT/'report/evidence/b2-motion/a/result-normal.json').read_text())['requests']
 assert c.lines==expected
 receipt['verdict']='PASS'
except Budget:
 code=2;receipt['verdict']='INCOMPLETE_WALL_BUDGET';receipt['limitation']='No functional success claimed. Increase --seconds for the complete original100MHz netlist.'
except Exception as e:
 code=1;receipt['verdict']='FAIL';receipt['error']=repr(e)
finally:
 receipt.update(exit_code=code,wall_seconds=time.monotonic()-start,simulated_us=c.us,state=c.state,requests=c.lines,response=bytes(c.from_mcu).decode(errors='replace'),trace=c.trace)
 (s/'result.json').write_text(json.dumps(receipt,indent=2));c.close();print(receipt['verdict'],code,receipt['simulated_us']);raise SystemExit(code)
