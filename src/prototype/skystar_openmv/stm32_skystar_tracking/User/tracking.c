#include "tracking.h"
#include <string.h>

static void history(tracking_t *c)
{
    pid_reset(&c->pan_pid); pid_reset(&c->tilt_pid);
    c->filter_ready = 0;
    c->raw_dx = c->raw_dy = c->filt_dx = c->filt_dy = 0;
}
static void invalidate(tracking_t *c)
{
    history(c); c->valid = 0; c->dx = c->dy = 0;
    /* Hold the last commanded pulse after target loss; stop/fault still disable. */
}
void tracking_init(tracking_t *c)
{
    memset(c, 0, sizeof(*c));
    /* Defaults retained from stm32_project/User/main.c. */
    /* Limit PID output/integral to the actual commanded pulse windows. */
    pid_init(&c->pan_pid, 3.0f, 0.5f, 0.0f,
             (float)PAN_MIN_US - PAN_HOME_US, (float)PAN_MAX_US - PAN_HOME_US);
    pid_init(&c->tilt_pid, 5.0f, 0.8f, 0.0f,
             (float)TILT_MIN_US - TILT_HOME_US, (float)TILT_MAX_US - TILT_HOME_US);
    c->pan_us = PAN_HOME_US; c->tilt_us = TILT_HOME_US;
}
void tracking_stop(tracking_t *c)
{
    c->outputs = 0; c->automatic = 0; invalidate(c);
}
void tracking_auto(tracking_t *c)
{
    tracking_stop(c); c->automatic = 1;
}
void tracking_reject(tracking_t *c)
{
    ++c->rejected; invalidate(c);
    if (c->automatic) c->outputs = 0; /* malformed or stale frame */
}
void tracking_tick(tracking_t *c, uint32_t now)
{
    if (c->valid && (uint32_t)(now - c->received_ms) >= FRAME_TIMEOUT_MS)
        invalidate(c);
}
static float limit_input(float next, float previous)
{
    if (next > previous + 40.0f) return previous + 40.0f;
    if (next < previous - 40.0f) return previous - 40.0f;
    return next;
}
static uint16_t pulse(float correction, uint16_t home, uint16_t old,
                      int32_t step, uint16_t lo, uint16_t hi)
{
    int32_t value = (int32_t)home + (int32_t)correction;
    if (value > (int32_t)old + step) value = (int32_t)old + step;
    if (value < (int32_t)old - step) value = (int32_t)old - step;
    if (value < lo) value = lo;
    if (value > hi) value = hi;
    return (uint16_t)value;
}
/* Preserve the held output as the PID baseline while correction is paused. */
static void hold_baseline(pid_t *pid, uint16_t current, uint16_t home)
{
    if (pid->Ki > 0.0f) pid->integral = (float)((int32_t)current - home);
    else pid->integral = 0.0f;
    pid->prev_error = 0.0f;
}
void tracking_observe(tracking_t *c, int16_t dx, int16_t dy,
                      uint8_t valid, uint32_t received, uint32_t now)
{
    float dt;
    int32_t step, tilt_step;
    tracking_tick(c, now);
    if (valid > 1 || dx < -80 || dx > 79 || dy < -59 || dy > 60 ||
        (!valid && (dx || dy)) || (uint32_t)(now - received) >= FRAME_TIMEOUT_MS) {
        tracking_reject(c); return;
    }
    dt = c->filter_ready ? (float)(uint32_t)(received - c->received_ms) / 1000.0f : 0.01f;
    if (dt <= 0 || dt > 0.2f) dt = 0.01f;
    c->received_ms = received; ++c->frames;
    if (!valid) { invalidate(c); return; }
    c->dx = dx; c->dy = dy; c->valid = 1;
    if (!c->automatic) return;
    if (!c->filter_ready) {
        c->raw_dx = c->filt_dx = (float)dx;
        c->raw_dy = c->filt_dy = (float)dy;
        if (c->outputs) {
            hold_baseline(&c->pan_pid, c->pan_us, PAN_HOME_US);
            hold_baseline(&c->tilt_pid, c->tilt_us, TILT_HOME_US);
        }
        c->pan_pid.prev_error = c->filt_dx;
        c->tilt_pid.prev_error = c->filt_dy;
        c->filter_ready = 1;
    } else {
        c->raw_dx = limit_input((float)dx, c->raw_dx);
        c->raw_dy = limit_input((float)dy, c->raw_dy);
        c->filt_dx += 0.35f * (c->raw_dx - c->filt_dx);
        c->filt_dy += 0.20f * (c->raw_dy - c->filt_dy);
    }
    step = (int32_t)(3.0f * dt / 0.01f + 0.5f);
    if (step < 1) step = 1;
    if (step > 15) step = 15;
    /* Limit each tilt change as well as its absolute pulse range. */
    tilt_step = (int32_t)(3.0f * dt / 0.01f + 0.5f);
    if (tilt_step < 1) tilt_step = 1;
    if (tilt_step > 15) tilt_step = 15;
    /* 2026-10-30 mount test: +25us reduces both measured dx and dy. */
    if (c->filt_dx > 3 || c->filt_dx < -3)
        c->pan_us = pulse(pid_update(&c->pan_pid, 0, -c->filt_dx, dt),
                         PAN_HOME_US, c->pan_us, step, PAN_MIN_US, PAN_MAX_US);
    else hold_baseline(&c->pan_pid, c->pan_us, PAN_HOME_US);
    if (c->filt_dy > 3 || c->filt_dy < -3)
        c->tilt_us = pulse(pid_update(&c->tilt_pid, 0, -c->filt_dy, dt),
                          TILT_HOME_US, c->tilt_us, tilt_step, TILT_MIN_US, TILT_MAX_US);
    else hold_baseline(&c->tilt_pid, c->tilt_us, TILT_HOME_US);
    c->outputs = 1;
}
void vision_init(vision_parser_t *p) { memset(p, 0, sizeof(*p)); }
int vision_feed(vision_parser_t *p, tracking_t *c, uint8_t byte,
                uint32_t received, uint32_t now)
{
    int16_t dx, dy;
    if (p->used && (uint32_t)(received - p->last_ms) >= BYTE_TIMEOUT_MS) {
        p->used = 0; tracking_reject(c);
    }
    p->last_ms = received;
    if (!p->used && byte != 0xAA) return 0;
    if (p->used == 1 && byte != 0xFF) {
        p->used = byte == 0xAA ? 1 : 0; return 0;
    }
    p->data[p->used++] = byte;
    if (p->used < 8) return 0;
    if (p->data[7] == 0xEE) {
        dx = (int16_t)((uint16_t)p->data[2] | ((uint16_t)p->data[3] << 8));
        dy = (int16_t)((uint16_t)p->data[4] | ((uint16_t)p->data[5] << 8));
        tracking_observe(c, dx, dy, p->data[6], received, now);
        p->used = 0; return 1;
    }
    tracking_reject(c);
    /* Retain the earliest embedded header after a truncated/bad frame. */
    { unsigned i;
      for (i = 1; i < 7; ++i) if (p->data[i] == 0xAA && p->data[i+1] == 0xFF) break;
      if (i < 7) { memmove(p->data, p->data+i, 8-i); p->used = (uint8_t)(8-i); }
      else { p->used = byte == 0xAA ? 1 : 0; p->data[0] = 0xAA; }
    }
    return -1;
}
static int number(const char *s, float *out)
{
    float value = 0, scale = 0.1f;
    unsigned digits = 0;
    while (*s == ' ') ++s;
    while (*s >= '0' && *s <= '9') {
        value = value * 10 + (*s++ - '0'); ++digits;
        if (value > 10000) return 0;
    }
    if (*s == '.') { ++s; while (*s >= '0' && *s <= '9') {
        value += (*s++ - '0') * scale; scale *= 0.1f; ++digits;
    }}
    while (*s == ' ') ++s;
    if (!digits || *s) return 0;
    *out = value; return 1;
}
int tracking_command(tracking_t *c, const char *s)
{
    float value;
    pid_t *pid;
    if (!strcmp(s,"st")) return 1;
    if (!strcmp(s,"stop")) { tracking_stop(c); return 1; }
    if (!strcmp(s,"auto")) { tracking_auto(c); return 1; }
    if (!strcmp(s,"home")) {
        tracking_stop(c); c->pan_us = PAN_HOME_US; c->tilt_us = TILT_HOME_US;
        c->outputs = 1; return 1;
    }
    if (strlen(s) < 5 || s[3] != ' ' || !number(s+4,&value)) return 0;
    if (!strncmp(s,"pan ",4) || !strncmp(s,"tlt ",4)) {
        int tilt = s[0] == 't';
        if (value != (float)(uint16_t)value ||
            value < (tilt ? TILT_MIN_US : PAN_MIN_US) ||
            value > (tilt ? TILT_MAX_US : PAN_MAX_US)) return 0;
        tracking_stop(c);
        if (tilt) c->tilt_us = (uint16_t)value; else c->pan_us = (uint16_t)value;
        c->outputs = 1; return 1;
    }
    if ((s[0]!='p' && s[0]!='t') || s[1]!='k' ||
        (s[2]!='p' && s[2]!='i' && s[2]!='d') || value > 50) return 0;
    pid = s[0]=='p' ? &c->pan_pid : &c->tilt_pid;
    if (s[2]=='p') pid->Kp=value;
    else if (s[2]=='i') pid->Ki=value;
    else pid->Kd=value;
    invalidate(c); return 1;
}
