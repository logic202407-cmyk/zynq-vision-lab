"""Instrument private copies of actual sources; production files remain unchanged."""
from pathlib import Path
import argparse,subprocess,json,hashlib,ctypes as C,shutil
from check_motion_cosim import ROOT,FW
p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--cc',required=True);a=p.parse_args();s=a.stage.absolute();s.mkdir(parents=True,exist_ok=False)
files=['board.c','main.c','s1ack.h','safety.c','safety.h','tracking.c','tracking.h','board.h']
hashes={};hooks={}
for n in files:
 t=(FW/'user'/n).read_text();hashes[n]=hashlib.sha256((FW/'user'/n).read_bytes()).hexdigest()
 if n=='board.c':
  t=t.replace('#define __disable_irq() ((void)0)','#define __disable_irq() b3_disable()').replace('#define __enable_irq() ((void)0)','#define __enable_irq() b3_enable()')
 replacements={
 'main.c':[(1,'accepted=safety_command(&guardian,&control,command,received,now);',False),(2,'if (accepted && (prior_state!=guardian.state ||',False),(3,'else if (accepted && !board_guard_refresh',False),(4,'poll_safety(now);',False),(5,'ack_reply(&request,accepted);',False),(6,'ack_reply(&request,accepted);',True)],
 'board.c':[(10,'if (enabled && (pan<PAN_MIN_US',False),(11,'if (!guard_active || guard_event || fault || board_button() ||',False),(12,'R(TIM4+0x34)=pan; R(TIM4+0x38)=tilt;',False),(13,'R(TIM4+0x34)=pan; R(TIM4+0x38)=tilt;',True),(14,'R(TIM4+0x20)=(1u<<0)|(1u<<4); pwm_enabled=1;',False),(15,'R(TIM4+0x20)=(1u<<0)|(1u<<4); pwm_enabled=1;',True),(16,'cc=R(TIM4+0x20); mode=R(GPIOD);',False),(17,'*pan=R(TIM4+0x34); *tilt=R(TIM4+0x38);',True)],
 's1ack.h':[(20,'board_pwm_snapshot(&mask,&pan,&tilt);',False),(21,'board_pwm_snapshot(&mask,&pan,&tilt);',True),(22,'if(accepted && r->kind==2 &&',False),(23,'if(r->kind==1 && !strcmp(r->op,"st")) {',False),(24,'if(m!=6 || !board_send(text))',False),(25,'if(m!=6 || !board_send(text))',True)]}.get(n,[])
 # Do not insert between an if and else; point3 belongs inside the condition via comma expression.
 for id,anchor,after in replacements:
  matches=[l for l in t.splitlines() if anchor in l];assert matches,(n,id)
  line=matches[0]
  if id==3:new=line.replace('!board_guard_refresh','(b3_hook(3),!board_guard_refresh').replace('guardian.live_ms))','guardian.live_ms)))')
  else:new=(line+'\n b3_hook(%d);'%id) if after else (' b3_hook(%d);\n'%id+line)
  t=t.replace(line,new,1);hooks[id]={'file':n,'anchor':anchor,'after':after}
 if replacements:t='void b3_hook(unsigned);void b3_disable(void);void b3_enable(void);\n'+t
 (s/n).write_text(t)
shutil.copyfile(ROOT/'sim/cosim/stm32_adapter.c',s/'stm32_adapter.c');shutil.copyfile(ROOT/'sim/cosim/b3_interrupt_driver.c',s/'driver.c')
cmd=[a.cc,'-shared','-std=c99','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-O0','-DBOARD_HOST_TEST','-DS1ACK1','-DCONSOLE_USART=3','-I'+str(s),'-I'+str(FW.parent/'stm32_project/user'),str(s/'driver.c'),str(s/'safety.c'),str(s/'tracking.c'),str(FW.parent/'stm32_project/user/pid.c'),'-o',str(s/'interrupt.dll')]
r=subprocess.run(cmd,capture_output=True);(s/'compile.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,(r.stdout,r.stderr)
d=C.CDLL(str(s/'interrupt.dll'));rows=[]
for axis in (0,1):
 for id in sorted(hooks):
  for ev in (1,2,3,4):
   fail=d.b3_case(id,ev,axis);out=bytearray()
   while True:
    b=d.model_transmit()
    if b<0:break
    out.append(b)
   rows.append({'axis':axis,'point':id,'event':ev,'failure_bits':fail,'reason':d.b3_reason(),'hit':d.b3_hit(),'max_masked_hook_steps':d.b3_mask_steps(),'response':out.decode(errors='replace')})
result={'scope':'statement-boundary scheduler, modeled PRIMASK deferral; not exhaustive Cortex-M instruction races','compile_command':cmd,'compile_exit':r.returncode,'source_sha256':hashes,'hooks':hooks,'count':len(rows),'passed':sum(x['failure_bits']==0 for x in rows),'failed':sum(x['failure_bits']!=0 for x in rows),'rows':rows}
result['reset_old_commands']=[{'partial':i,'failure':d.b3_reset_old(i)} for i in (0,1)]
result['exit_code']=int(result['failed']>0 or any(x['failure'] for x in result['reset_old_commands']));(s/'result.json').write_text(json.dumps(result,indent=2));print('INTERRUPTS',result['passed'],result['failed']);raise SystemExit(result['exit_code'])
