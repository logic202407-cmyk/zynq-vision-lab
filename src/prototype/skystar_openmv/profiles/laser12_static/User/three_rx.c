#include "board.h"
#include "tracking.h"
#include <stdio.h>
static vision_parser_t parsers[3];
static tracking_t tracks[3];
static uint32_t next_log;
void three_rx_init(void){unsigned i;for(i=0;i<3;i++){vision_init(&parsers[i]);tracking_init(&tracks[i]);}}
void three_rx_tick(uint32_t now){unsigned id,n;uint8_t b;uint32_t received;char line[140];
 for(id=0;id<3;id++){
  for(n=0;n<64 && board_camera_byte(id,&b,&received);n++)vision_feed(&parsers[id],&tracks[id],b,received,now);
  tracking_tick(&tracks[id],now);
 }
 if((uint32_t)(now-next_log)>=500u){next_log=now;
  for(id=0;id<3;id++){
   tracking_t *c=&tracks[id];
   snprintf(line,sizeof(line),"RX3 ID=%u FR=%lu BAD=%lu VALID=%u DX=%d DY=%d AGE=%lu PWM=0 MODE=STATIC_LASER12_TEST\r\n",id+1,(unsigned long)c->frames,(unsigned long)c->rejected,(unsigned)c->valid,(int)c->dx,(int)c->dy,(unsigned long)(now-c->received_ms));
   board_send(line);
  }
 }
}
