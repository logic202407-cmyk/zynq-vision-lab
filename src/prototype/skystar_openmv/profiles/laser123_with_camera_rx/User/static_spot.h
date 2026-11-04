#ifndef STATIC_SPOT_H
#define STATIC_SPOT_H
#include <stdint.h>
typedef struct { uint32_t since; uint8_t state; } static_spot_t;
uint8_t static_spot_tick(static_spot_t *s,uint32_t now,uint8_t permit,int16_t dx,int16_t dy);
#endif
