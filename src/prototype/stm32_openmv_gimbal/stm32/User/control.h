#ifndef P0_CONTROL_H
#define P0_CONTROL_H
#include "pid.h"
#include "uart_parser.h"
#define FRAME_TIMEOUT_MS 200u
#define PAN_HOME_US 1450u
#define TILT_HOME_US 1500u
#define PAN_SAFE_MIN 600u
#define PAN_SAFE_MAX 2400u
#define TILT_SAFE_MIN 1000u
#define TILT_SAFE_MAX 2400u
typedef enum { OBS_WAITING, OBS_TRACKING, OBS_NO_TARGET, OBS_TIMEOUT, OBS_REJECTED } observation_t;
typedef struct {
    pid_t pan_pid, tilt_pid;
    float filt_dx, filt_dy, raw_dx, raw_dy;
    uint32_t session, frame, received_ms, source_ms, rejected, recoveries;
    uint32_t now_ms, resume_ms;
    uint16_t pan_us, tilt_us, requested_pan, requested_tilt;
    int16_t dx, dy;
    uint8_t have_frame, valid, manual, auto_enabled, filter_ready, updated, need_new_frame;
    observation_t state;
    reject_t last_reject;
} control_t;
void control_init(control_t *c);
void control_invalidate(control_t *c, reject_t reason);
void control_tick(control_t *c, uint32_t now_ms);
int control_frame(control_t *c, const track_target_t *t, uint32_t now_ms);
int control_manual(control_t *c, int tilt_axis, uint16_t pulse);
void control_auto(control_t *c);
void control_parameters_changed(control_t *c);
const char *observation_name(observation_t state);
#endif
