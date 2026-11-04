#include "vision_measurement.h"
#include "safety.h"
#include <string.h>
static uint16_t u16(const uint8_t*p){return (uint16_t)(((uint16_t)p[0]<<8)|p[1]);}
static uint32_t u32(const uint8_t*p){return ((uint32_t)u16(p)<<16)|u16(p+2);}
int measurement_decode(const uint8_t *p,unsigned n,measurement_t *out){
 measurement_t m;
 if(n!=M2_BYTES||p[0]!=0xa5||p[1]!=0x5a||p[2]!=2||p[3]!=1||
    safety_crc((const char*)p,52)!=u16(p+52))return 0;
 m.camera=p[4];m.flags=p[5];m.origin=p[6];m.mask=p[7];
 m.session_hi=u32(p+8);m.session_lo=u32(p+12);m.sequence=u32(p+16);m.tick=u32(p+20);
 m.width=u16(p+24);m.height=u16(p+26);m.count=u32(p+28);m.sum_x=u32(p+32);m.sum_y=u32(p+36);
 m.xmin=u16(p+40);m.ymin=u16(p+42);m.xmax=u16(p+44);m.ymax=u16(p+46);m.cx=u16(p+48);m.cy=u16(p+50);
 if(m.camera>=M2_CAMERAS||(m.origin!=1&&m.origin!=2)||(m.mask!=1&&m.mask!=2)||
    (!m.session_hi&&!m.session_lo)||(m.flags&~7)||!m.width||m.width>640||!m.height||m.height>480||
    (!(m.flags&4)&&m.tick))return 0;
 if(!(m.flags&2)){
  if(m.count||m.sum_x||m.sum_y||m.xmin||m.ymin||m.xmax||m.ymax||m.cx||m.cy)return 0;
 }else{
  if(!(m.flags&1)||!m.count||m.count>(uint32_t)m.width*m.height)return 0;
  if(m.xmin>m.cx||m.cx>m.xmax||m.xmax>=m.width||m.ymin>m.cy||m.cy>m.ymax||m.ymax>=m.height||
     m.sum_x>m.count*(m.width-1)||m.sum_y>m.count*(m.height-1)||m.cx!=m.sum_x/m.count||m.cy!=m.sum_y/m.count)return 0;
 }
 *out=m;return 1;
}
int measurement_bind(measurement_store_t*s,unsigned camera,uint32_t hi,uint32_t lo){
 measurement_slot_t *v;if(camera>=M2_CAMERAS||(!hi&&!lo))return 0;
 v=&s->camera[camera];memset(v,0,sizeof(*v));v->session_hi=hi;v->session_lo=lo;v->session_bound=1;return 1;
}
int measurement_receive(measurement_store_t*s,const uint8_t*p,unsigned n,uint32_t received,uint32_t now){
 measurement_t m;measurement_slot_t*v;
 if(!measurement_decode(p,n,&m)||m.origin!=1)return 0; /* PC reference is not PL authority. */
 v=&s->camera[m.camera];
 if(!v->session_bound||v->session_hi!=m.session_hi||v->session_lo!=m.session_lo||
    (uint32_t)(now-received)>=200u||(v->seen&&m.sequence<=v->value.sequence)){
  ++v->rejected;return 0;
 }
 if(v->seen)v->gaps+=m.sequence-v->value.sequence-1;
 v->value=m;v->seen=v->fresh=1;v->rx_ms=received;++v->accepted;return 1;
}
void measurement_tick(measurement_store_t*s,uint32_t now){
 unsigned i;for(i=0;i<M2_CAMERAS;i++)if((uint32_t)(now-s->camera[i].rx_ms)>=200u)s->camera[i].fresh=0;
}
