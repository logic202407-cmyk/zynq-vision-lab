#ifndef VISION_MEASUREMENT_H
#define VISION_MEASUREMENT_H
#include <stdint.h>
#define M2_BYTES 54u
#define M2_CAMERAS 4u
typedef struct {
 uint8_t camera,flags,origin,mask;
 uint32_t session_hi,session_lo,sequence,tick;
 uint16_t width,height;
 uint32_t count,sum_x,sum_y;
 uint16_t xmin,ymin,xmax,ymax,cx,cy;
} measurement_t;
typedef struct {
 measurement_t value;
 uint32_t accepted, rejected, gaps, rx_ms, session_hi, session_lo;
 uint8_t session_bound, seen, fresh;
} measurement_slot_t;
typedef struct { measurement_slot_t camera[M2_CAMERAS]; } measurement_store_t;
int measurement_decode(const uint8_t *p,unsigned size,measurement_t *out);
/* Explicit session binding is a logging operation; it never authorizes motion. */
int measurement_bind(measurement_store_t *s,unsigned camera,uint32_t hi,uint32_t lo);
int measurement_receive(measurement_store_t *s,const uint8_t *p,unsigned size,uint32_t received,uint32_t now);
void measurement_tick(measurement_store_t *s,uint32_t now);
#endif
