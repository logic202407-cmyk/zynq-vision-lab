#include "laser_lock.h"
#include <string.h>

void laser_lock_reset(laser_lock_t *lock)
{
    memset(lock, 0, sizeof(*lock));
}

void laser_lock_frame(laser_lock_t *lock, uint32_t received_ms, uint8_t valid)
{
    lock->have_frame = 1;
    lock->received_ms = received_ms;
    /* A fresh detected target is sufficient; position and motion do not gate PB0. */
    lock->on = (valid == 1);
}

uint8_t laser_lock_tick(laser_lock_t *lock, uint32_t now_ms, uint8_t enabled)
{
    if (!enabled || !lock->have_frame ||
        (uint32_t)(now_ms - lock->received_ms) >= LASER_FRAME_TIMEOUT_MS) {
        laser_lock_reset(lock);
    }
    return lock->on;
}
