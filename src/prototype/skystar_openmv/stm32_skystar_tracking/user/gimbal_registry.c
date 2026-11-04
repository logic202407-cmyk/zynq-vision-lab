#include "gimbal_registry.h"
#include <string.h>
const gimbal_pwm_resource_t gimbal_pwm_resources[6]={
#define GIMBAL_PWM(id, axis, pin, timer, channel, af) {id,axis,1,1,#pin,#timer,channel,af},
#define GIMBAL_RX(id, pin, uart, af)
#include "gimbal_wiring.def"
#undef GIMBAL_PWM
#undef GIMBAL_RX
};
const gimbal_rx_resource_t gimbal_rx_resources[GIMBAL_COUNT]={
#define GIMBAL_PWM(id, axis, pin, timer, channel, af)
#define GIMBAL_RX(id, pin, uart, af) {id,#pin,#uart,af},
#include "gimbal_wiring.def"
#undef GIMBAL_PWM
#undef GIMBAL_RX
};
void gimbal_registry_init(gimbal_registry_t *r){
 unsigned i;memset(r,0,sizeof(*r));
 for(i=0;i<GIMBAL_COUNT;i++){
  gimbal_context_t *g=&r->devices[i];g->id=(uint8_t)i;g->installed=(i==0);
  g->primary_camera=i==0?0:255;g->auxiliary_camera=(uint8_t)(i+1);
  tracking_init(&g->control);vision_init(&g->openmv_parser);
  safety_init(&g->safety_snapshot,0,0,0);
 }
}
int gimbal_record_targets(gimbal_registry_t *r,unsigned id,unsigned pan,unsigned tilt){
 if(id>=GIMBAL_COUNT||pan<PAN_MIN_US||pan>PAN_MAX_US||tilt<TILT_MIN_US||tilt>TILT_MAX_US)return 0;
 r->devices[id].control.pan_us=(uint16_t)pan;
 r->devices[id].control.tilt_us=(uint16_t)tilt;return 1;
}
int gimbal_openmv_byte(gimbal_registry_t *r,unsigned id,uint8_t b,uint32_t received,uint32_t now){
 gimbal_context_t *g;uint32_t frames;int result;
 if(id>=GIMBAL_COUNT||!r->devices[id].installed)return 0;
 g=&r->devices[id];frames=g->control.frames;
 /* Never call the existing auto/PID actuation path from measurement ingestion. */
 g->control.automatic=0;g->control.outputs=0;
 result=vision_feed(&g->openmv_parser,&g->control,b,received,now);
 if(g->control.frames!=frames){g->last_rx_ms=received;g->communication_valid=1;}
 return result;
}
void gimbal_registry_tick(gimbal_registry_t *r,uint32_t now){
 unsigned i;for(i=0;i<GIMBAL_COUNT;i++){
  gimbal_context_t *g=&r->devices[i];tracking_tick(&g->control,now);
  if((uint32_t)(now-g->last_rx_ms)>=FRAME_TIMEOUT_MS)g->communication_valid=0;
 }
}
void gimbal_registry_stop(gimbal_registry_t *r,unsigned id,uint8_t fault){
 if(id<GIMBAL_COUNT){tracking_stop(&r->devices[id].control);r->devices[id].owner=0;
  if(!r->devices[id].fault)r->devices[id].fault=fault;
 }
}
