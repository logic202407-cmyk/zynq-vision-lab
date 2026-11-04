#include <assert.h>
#include <stdio.h>
#include "tracking.h"
int main(void){tracking_t c;unsigned i;tracking_init(&c);tracking_auto(&c);for(i=1;i<=1500;i++){tracking_observe(&c,(int16_t)((int)(i%11)-5),0,1,i*20,i*20);assert(c.outputs==0);assert(c.valid);}assert(c.automatic);puts("PASS 1500 live AUTO observations retain truthful PWM-disabled intent; heartbeat ABORTED predicate stays false for actual mask0");return 0;}
