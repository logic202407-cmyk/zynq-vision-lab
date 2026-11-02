/* Test-only statement-boundary preemption. Not an ARM instruction emulator. */
#include "stm32_adapter.c"
static unsigned selected,event_id,hit,masked,pending,nested,latched,max_mask_steps,mask_steps;
static unsigned reason_first;
static void dispatch(void) {
 if(nested)return;nested=1;
 if(event_id==1){milliseconds=guard_received+499;SysTick_Handler();}
 if(event_id==2)model_receive('!',1);
 if(event_id==3){unsigned i;for(i=0;i<256;i++)model_receive('\r',0);}
 if(event_id==4){R(GPIOA+0x10)=1;SysTick_Handler();R(GPIOA+0x10)=0;}
 latched=1;nested=0;
}
void b3_disable(void){masked=1;mask_steps=0;}
void b3_enable(void){masked=0;if(mask_steps>max_mask_steps)max_mask_steps=mask_steps;if(pending){pending=0;dispatch();}}
void b3_hook(unsigned id){
 if(nested)return;if(masked)++mask_steps;
 if(selected==id&&!hit){hit=1;if(masked)pending=1;else dispatch();}
}
static void send_body(const char *body,int newline){
 char s[160];unsigned i;snprintf(s,sizeof(s),"%s*%04x%s",body,safety_crc(body,(unsigned)strlen(body)),newline?"\n":"");
 for(i=0;s[i];i++){model_receive((unsigned char)s[i],0);model_foreground();}
}
API unsigned b3_case(unsigned point,unsigned ev,unsigned axis){
 char body[120];unsigned fail=0;
 selected=hit=masked=pending=nested=latched=max_mask_steps=mask_steps=0;event_id=ev;
 model_init();snprintf(body,sizeof(body),"s1 %08lx%08lx 0 arm",(unsigned long)guardian.nonce_hi,(unsigned long)guardian.nonce_lo);send_body(body,1);
 snprintf(body,sizeof(body),"s1 %08lx%08lx 1 %s 1550",(unsigned long)guardian.nonce_hi,(unsigned long)guardian.nonce_lo,axis?"tlt":"pan");send_body(body,0);
 selected=point;model_receive(10,0);model_foreground();selected=0;
 poll_safety(board_ms());board_outputs(safety_armed(&guardian)&&control.outputs,control.pan_us,control.tilt_us);
 reason_first=guardian.reason;
 if(!hit)fail|=1;
 if(R(TIM4+0x20)!=0||guardian.state!=SAFE_FAULT)fail|=2;
 if(reason_first!=(ev==1?SAFE_LINK_TIMEOUT:ev==4?SAFE_KEY:SAFE_UART))fail|=4;
 // A later different error must not erase the already latched reason.
 model_receive('!',1);poll_safety(board_ms());board_outputs(1,1600,1600);
 if(guardian.reason!=reason_first||R(TIM4+0x20)!=0)fail|=8;
 return fail;
}
API unsigned b3_reason(void){return reason_first;}
API unsigned b3_hit(void){return hit;}
API unsigned b3_mask_steps(void){return max_mask_steps;}

API unsigned b3_reset_old(unsigned partial) {
 char body[120],wire[160];unsigned i,n,fail=0;
 selected=hit=masked=pending=nested=latched=0;
 model_init();snprintf(body,sizeof(body),"s1 %08lx%08lx 0 arm",(unsigned long)guardian.nonce_hi,(unsigned long)guardian.nonce_lo);
 snprintf(wire,sizeof(wire),"%s*%04x\n",body,safety_crc(body,(unsigned)strlen(body)));n=(unsigned)strlen(wire);
 if(partial)for(i=0;i<n/2;i++){model_receive(wire[i],0);model_foreground();}
 model_reboot();
 for(i=partial?n/2:0;i<n;i++){model_receive(wire[i],0);model_foreground();}
 if(safety_armed(&guardian)||R(TIM4+0x20)!=0)fail=1;
 return fail;
}
