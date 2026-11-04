#include "tracking.h"
#include "safety.h"
#include "speed_axis.h"
#include <stdio.h>
static int failures;
#define CHECK(c,m) do{printf("%s %s\n",(c)?"PASS":"FAIL",m);if(!(c))failures++;}while(0)
int main(void){tracking_t c;safety_t s;int e;uint32_t t;
 for(e=-80;e<=79;e++){uint16_t p=speed_axis_pulse(e,1500,1);if(p<1492||p>1508)failures++;if(e>4&&p<=1500)failures++;if(e<-4&&p>=1500)failures++;}
 CHECK(!failures,"all legal errors bounded and on correct side of neutral");
 tracking_init(&c);tracking_auto(&c);safety_init(&s,1,2,1);s.state=SAFE_AUTO;s.mode_ms=10;s.live_ms=10;
 for(t=10;t<=50;t+=20)tracking_observe(&c,-48,-7,1,t,t);
 CHECK(c.outputs&&c.pan_us==1495,"three fresh frames acquire negative speed");
 tracking_observe(&c,7,-7,1,70,70);CHECK(c.pan_us==1501,"sign reversal crosses neutral on first frame");
 tracking_observe(&c,0,-7,1,90,90);CHECK(c.pan_us==1500,"zero error commands nominal stop, no old-speed hold");
 tracking_observe(&c,0,0,0,110,110);CHECK(!c.outputs&&c.automatic&&c.pan_us==1500,"single missing frame disables outputs, preserves bounded acquisition");
 safety_tick(&s,&c,110);CHECK(s.state==SAFE_AUTO,"short dropout does not latch fault");
 tracking_observe(&c,-20,-7,1,130,130);tracking_observe(&c,-20,-7,1,150,150);CHECK(!c.outputs,"two frames cannot restart output");
 tracking_observe(&c,-20,-7,1,170,170);CHECK(c.outputs&&c.pan_us==1498,"third fresh frame resumes speed correction");
 tracking_observe(&c,0,0,0,190,190);tracking_observe(&c,0,0,0,350,350);s.live_ms=350;safety_tick(&s,&c,369);CHECK(s.state==SAFE_AUTO,"invalid frames do not erase last-good timing");
 safety_tick(&s,&c,370);CHECK(s.state==SAFE_FAULT&&!c.outputs&&!c.automatic,"200ms continuous loss latches fault");
 tracking_observe(&c,-20,-7,1,390,390);CHECK(!c.outputs&&!c.automatic,"target return cannot clear long-loss fault");
 tracking_auto(&c);s.state=SAFE_AUTO;s.mode_ms=400;s.live_ms=400;tracking_observe(&c,-20,-7,1,410,410);tracking_stop(&c);CHECK(!c.automatic&&!c.outputs,"explicit stop never auto-restarts");
 printf("failures=%d\n",failures);return failures?1:0;}
