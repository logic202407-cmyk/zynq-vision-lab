#include "gimbal_registry.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static void frame(gimbal_registry_t*r,unsigned id,int x,int y,int valid,unsigned t){
 unsigned i;unsigned char b[8]={0xaa,0xff,(unsigned char)x,(unsigned char)(x>>8),(unsigned char)y,(unsigned char)(y>>8),(unsigned char)valid,0xee};
 for(i=0;i<8;i++)gimbal_openmv_byte(r,id,b[i],t,t);
}
int main(void){
 gimbal_registry_t r;unsigned i;int x[4]={20,-20,-20,20},y[4]={20,20,-20,-20};
 gimbal_registry_init(&r);assert(r.devices[0].installed&&!r.devices[1].installed&&!r.devices[2].installed);
 for(i=0;i<3;i++){assert(gimbal_record_targets(&r,i,1510+i*10,1490-i*10));r.devices[i].control.pan_pid.integral=(float)(i+1);}
 for(i=0;i<3;i++){assert(r.devices[i].control.pan_us==1510+i*10);assert(r.devices[i].control.tilt_us==1490-i*10);assert(r.devices[i].control.pan_pid.integral==(float)(i+1));assert(!r.devices[i].control.outputs);}
 assert(!gimbal_record_targets(&r,3,1500,1500));assert(!gimbal_record_targets(&r,0,1701,1500));
 for(i=0;i<4;i++){frame(&r,0,x[i],y[i],1,10+i);assert(r.devices[0].control.dx==x[i]&&r.devices[0].control.dy==y[i]&&r.devices[0].control.valid);}
 frame(&r,1,20,20,1,20);assert(!r.devices[1].control.frames);
 frame(&r,0,0,0,0,20);assert(!r.devices[0].control.valid&&r.devices[0].communication_valid);
 frame(&r,0,100,0,1,21);assert(!r.devices[0].control.valid);
 gimbal_registry_tick(&r,220);assert(!r.devices[0].communication_valid);
 gimbal_registry_stop(&r,0,3);assert(r.devices[0].fault==3&&!r.devices[1].fault&&!r.devices[2].fault);
 for(i=0;i<6;i++){
  unsigned j;const gimbal_pwm_resource_t *p=&gimbal_pwm_resources[i];
  assert(p->mapped&&p->confirmed_for_preparation);
  assert(p->gimbal==i/2&&p->axis==i%2);
  for(j=0;j<i;j++){
   const gimbal_pwm_resource_t *q=&gimbal_pwm_resources[j];
   assert(strcmp(p->pin,q->pin));
   assert(strcmp(p->timer,q->timer)||p->channel!=q->channel);
  }
 }
 assert(!strcmp(gimbal_pwm_resources[4].pin,"PE9")&&gimbal_pwm_resources[4].channel==1);
 assert(!strcmp(gimbal_pwm_resources[5].pin,"PE11")&&gimbal_pwm_resources[5].channel==2);
 assert(!strcmp(gimbal_pwm_resources[4].timer,"TIM1")&&gimbal_pwm_resources[4].alternate_function==1);
 assert(!strcmp(gimbal_rx_resources[1].pin,"PC7")&&!strcmp(gimbal_rx_resources[1].uart,"USART6"));
 assert(!strcmp(gimbal_rx_resources[2].pin,"PD2")&&!strcmp(gimbal_rx_resources[2].uart,"UART5"));
 /* A selected map must not install/enable a new device or consume its data. */
 for(i=1;i<3;i++){
  frame(&r,i,20,20,1,230);
  assert(!r.devices[i].installed&&!r.devices[i].control.frames);
  assert(!r.devices[i].control.outputs&&!r.devices[i].pwm_enabled);
 }
 puts("C1_REGISTRY_PASS isolation, quadrants, loss, bounds, timeout, six-resource table; no hardware");return 0;
}
