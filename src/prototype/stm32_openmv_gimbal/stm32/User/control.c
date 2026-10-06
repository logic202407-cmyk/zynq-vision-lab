#include "control.h"
#include <string.h>

static void reset_history(control_t *c)
{
    pid_reset(&c->pan_pid);
    pid_reset(&c->tilt_pid);
    c->filter_ready = 0;
    c->filt_dx = c->filt_dy = c->raw_dx = c->raw_dy = 0;
    c->valid = c->auto_enabled = 0;
    c->dx = c->dy = 0;
    c->updated = 0;
    c->requested_pan = c->pan_us;
    c->requested_tilt = c->tilt_us;
}
void control_init(control_t *c)
{
    memset(c, 0, sizeof(*c));
    pid_init(&c->pan_pid, 3.0f, 0.5f, 0.0f, -750.0f, 750.0f);
    pid_init(&c->tilt_pid, 5.0f, 0.8f, 0.0f, -500.0f, 500.0f);
    c->pan_us = PAN_HOME_US;
    c->tilt_us = TILT_HOME_US;
    reset_history(c);
}
void control_invalidate(control_t *c, reject_t reason)
{
    reset_history(c);
    c->state = OBS_REJECTED;
    c->last_reject = reason;
    ++c->rejected;
}
void control_tick(control_t *c, uint32_t now_ms)
{
    c->now_ms = now_ms;
    c->updated = 0;
    if (c->have_frame && (uint32_t)(now_ms - c->received_ms) >= FRAME_TIMEOUT_MS) {
        reset_history(c);
        c->state = OBS_TIMEOUT;
    }
}
static float limited_input(float value, float previous)
{
    if (value > previous + 40.0f) return previous + 40.0f;
    if (value < previous - 40.0f) return previous - 40.0f;
    return value;
}
static uint16_t pulse(float correction, uint16_t home, uint16_t previous,
                      int32_t step, uint16_t lo, uint16_t hi)
{
    int32_t value = (int32_t)home + (int32_t)correction;
    if (value > (int32_t)previous + step) value = (int32_t)previous + step;
    if (value < (int32_t)previous - step) value = (int32_t)previous - step;
    if (value < lo) value = lo;
    if (value > hi) value = hi;
    return (uint16_t)value;
}
int control_frame(control_t *c, const track_target_t *t, uint32_t now_ms)
{
    uint8_t fresh_start;
    uint16_t old_pan = c->pan_us, old_tilt = c->tilt_us;
    float dt;
    int32_t step;
    control_tick(c, now_ms); /* Also detect a gap when no idle tick was called. */
    if ((uint32_t)(now_ms - t->received_ms) >= FRAME_TIMEOUT_MS) {
        control_invalidate(c, REJECT_STALE);
        return 0;
    }
    if (c->need_new_frame && (int32_t)(t->received_ms - c->resume_ms) < 0) {
        control_invalidate(c, REJECT_STALE);
        return 0;
    }
    if (c->have_frame && t->session < c->session) {
        control_invalidate(c, REJECT_SESSION);
        return 0;
    }
    if (c->have_frame && t->session == c->session && t->frame <= c->frame) {
        control_invalidate(c, REJECT_FRAME);
        return 0;
    }
    if (!c->have_frame || t->session != c->session) reset_history(c);
    fresh_start = !c->filter_ready;
    dt = fresh_start ? 0.01f : (float)(uint32_t)(t->received_ms - c->received_ms) / 1000.0f;
    if (dt <= 0.0f || dt > 0.2f) dt = 0.01f;
    c->session = t->session;
    c->frame = t->frame;
    c->received_ms = t->received_ms;
    c->source_ms = t->source_ms; /* Diagnostic only, never a freshness clock. */
    c->have_frame = 1;
    c->need_new_frame = 0;
    c->last_reject = REJECT_NONE;
    c->updated = 0;
    if (!t->valid) {
        reset_history(c);
        c->state = OBS_NO_TARGET;
        return 1;
    }
    c->dx = t->dx;
    c->dy = t->dy;
    c->valid = 1;
    c->state = OBS_TRACKING;
    c->auto_enabled = !c->manual;
    if (c->manual) return 1;
    if (fresh_start) {
        c->raw_dx = c->filt_dx = (float)t->dx;
        c->raw_dy = c->filt_dy = (float)t->dy;
        /* Initialize derivative to the current error; no recovery D kick. */
        c->pan_pid.prev_error = c->filt_dx;
        c->tilt_pid.prev_error = -c->filt_dy;
        c->filter_ready = 1;
        ++c->recoveries;
    } else {
        c->raw_dx = limited_input((float)t->dx, c->raw_dx);
        c->raw_dy = limited_input((float)t->dy, c->raw_dy);
        c->filt_dx += 0.35f * (c->raw_dx - c->filt_dx);
        c->filt_dy += 0.20f * (c->raw_dy - c->filt_dy);
    }
    step = (int32_t)(60.0f * dt / 0.01f + 0.5f);
    if (step < 60) step = 60;
    if (step > 350) step = 350;
    if (c->filt_dx > 3.0f || c->filt_dx < -3.0f)
        c->requested_pan = pulse(pid_update(&c->pan_pid, 0, -c->filt_dx, dt),
                                PAN_HOME_US, c->pan_us, step, PAN_SAFE_MIN, PAN_SAFE_MAX);
    else { pid_reset(&c->pan_pid); c->requested_pan = c->pan_us; }
    if (c->filt_dy > 3.0f || c->filt_dy < -3.0f)
        c->requested_tilt = pulse(pid_update(&c->tilt_pid, 0, c->filt_dy, dt),
                                 TILT_HOME_US, c->tilt_us, step, TILT_SAFE_MIN, TILT_SAFE_MAX);
    else { pid_reset(&c->tilt_pid); c->requested_tilt = c->tilt_us; }
    c->pan_us = c->requested_pan;
    c->tilt_us = c->requested_tilt;
    c->updated = c->pan_us != old_pan || c->tilt_us != old_tilt;
    return 1;
}
int control_manual(control_t *c, int tilt_axis, uint16_t value)
{
    if ((!tilt_axis && (value < PAN_SAFE_MIN || value > PAN_SAFE_MAX)) ||
        (tilt_axis && (value < TILT_SAFE_MIN || value > TILT_SAFE_MAX))) return 0;
    reset_history(c);
    c->manual = 1;
    c->last_reject = REJECT_NONE;
    c->state = OBS_WAITING;
    /* The other axis always comes from its most recently applied value. */
    if (tilt_axis) { c->updated = c->tilt_us != value; c->tilt_us = value; }
    else { c->updated = c->pan_us != value; c->pan_us = value; }
    c->requested_pan = c->pan_us;
    c->requested_tilt = c->tilt_us;
    return 1;
}
void control_auto(control_t *c)
{
    reset_history(c);
    c->manual = 0;
    c->state = OBS_WAITING;
    c->last_reject = REJECT_NONE;
    c->resume_ms = c->now_ms;
    c->need_new_frame = 1;
    /* Retain session/frame high-water marks: queued old frames stay rejected. */
}
void control_parameters_changed(control_t *c)
{
    reset_history(c);
    c->state = OBS_WAITING;
    c->last_reject = REJECT_NONE;
    c->resume_ms = c->now_ms;
    c->need_new_frame = 1;
}
const char *observation_name(observation_t state)
{
    static const char *const names[] = { "waiting", "tracking", "no_target", "timeout", "rejected" };
    return names[(unsigned)state < sizeof(names) / sizeof(names[0]) ? state : OBS_REJECTED];
}
