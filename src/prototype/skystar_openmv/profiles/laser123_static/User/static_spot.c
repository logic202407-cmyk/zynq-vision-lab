#include "static_spot.h"
/* Manually authorized static illumination. Never enables servo outputs.
 * Fresh target required, no center gate. Loss after activation latches off.
 * STOP/key/lease are enforced independently by board and safety layers. */
uint8_t static_spot_tick(static_spot_t *s,uint32_t now,uint8_t permit,int16_t dx,int16_t dy)
{
    (void)dx; (void)dy;
    if(s->state==3) return 0;
    if(!permit) { s->state=s->state==2?3:0; return 0; }
    if(s->state==0) { s->since=now;s->state=1;return 0; }
    if(s->state==1) { if((uint32_t)(now-s->since)<1000u)return 0;s->state=2; }
    return 1;
}
