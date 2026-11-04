#ifndef STATIC_SPOT_H
#define STATIC_SPOT_H
#include <stdint.h>
#define SPOT_MAX_MS 200u
typedef struct { uint32_t since; uint8_t state; } static_spot_t;
uint8_t static_spot_tick(static_spot_t *s,uint32_t now,uint8_t permit,int16_t dx,int16_t dy);
#endif
