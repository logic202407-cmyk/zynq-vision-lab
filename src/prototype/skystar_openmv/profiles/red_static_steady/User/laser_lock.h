#ifndef LASER_LOCK_H
#define LASER_LOCK_H
#include <stdint.h>

#define LASER_FRAME_TIMEOUT_MS 200u

typedef struct {
    uint32_t received_ms;
    uint8_t have_frame, on;
} laser_lock_t;

void laser_lock_reset(laser_lock_t *lock);
void laser_lock_frame(laser_lock_t *lock, uint32_t received_ms, uint8_t valid);
uint8_t laser_lock_tick(laser_lock_t *lock, uint32_t now_ms, uint8_t enabled);
#endif
