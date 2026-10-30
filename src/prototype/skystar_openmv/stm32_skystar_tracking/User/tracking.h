#ifndef SKYSTAR_TRACKING_H
#define SKYSTAR_TRACKING_H
#include <stdint.h>
#include "pid.h"

/* Initial commissioning window, not a measured mechanical travel limit. */
#define PAN_HOME_US 1500u
#define TILT_HOME_US 1500u
#define PAN_MIN_US 1300u
#define PAN_MAX_US 1700u
#define TILT_MIN_US 1300u
#define TILT_MAX_US 1700u
#define FRAME_TIMEOUT_MS 200u
#define BYTE_TIMEOUT_MS 20u

typedef struct {
    pid_t pan_pid, tilt_pid;
    float raw_dx, raw_dy, filt_dx, filt_dy;
    uint32_t received_ms, frames, rejected;
    uint16_t pan_us, tilt_us;
    int16_t dx, dy;
    uint8_t valid, automatic, outputs, filter_ready;
} tracking_t;
typedef struct { uint8_t data[8], used; uint32_t last_ms; } vision_parser_t;

void tracking_init(tracking_t *c);
void tracking_stop(tracking_t *c);
void tracking_auto(tracking_t *c);
void tracking_tick(tracking_t *c, uint32_t now);
void tracking_observe(tracking_t *c, int16_t dx, int16_t dy,
                      uint8_t valid, uint32_t received, uint32_t now);
void tracking_reject(tracking_t *c);
void vision_init(vision_parser_t *p);
int vision_feed(vision_parser_t *p, tracking_t *c, uint8_t byte,
                uint32_t received, uint32_t now);
/* 1 accepted, 0 invalid; no command performs a Flash write. */
int tracking_command(tracking_t *c, const char *line);
#endif
