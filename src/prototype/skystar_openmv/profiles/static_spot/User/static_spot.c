#include "static_spot.h"
uint8_t static_spot_tick(static_spot_t *s,uint32_t now,uint8_t permit,int16_t dx,int16_t dy)
{
    uint8_t centered=(uint8_t)(permit && dx>=-3 && dx<=3 && dy>=-3 && dy<=3);
    if(s->state==3) return 0;
    if(!centered) { s->state=s->state==2?3:0; return 0; }
    if(s->state==0) { s->since=now;s->state=1;return 0; }
    if(s->state==1) { if((uint32_t)(now-s->since)<1000u)return 0;s->since=now;s->state=2; }
    if((uint32_t)(now-s->since)>=SPOT_MAX_MS) { s->state=3;return 0; }
    return 1;
}
