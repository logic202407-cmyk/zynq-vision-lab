#ifndef CIRCLE_DRAW_H
#define CIRCLE_DRAW_H

#include <stdint.h>

/* Portable trajectory/state machine: no GPIO, UART or delays here. */
typedef struct {
    float distance_mm, radius_mm;
    float pan_us_per_rad, tilt_us_per_rad;
    uint32_t period_ms;
    uint16_t center_pan, center_tilt;
    /* Dead-band lead per axis, in us. A servo only follows once the error
     * grows past its dead band, so a slow lap turns into stair steps. Adding
     * this lead along the current travel direction cancels most of that lag;
     * 0 disables the compensation and reproduces the old trajectory. */
    uint16_t pan_back_us, tilt_back_us;
    /* Single-stroke endpoints in paper millimetres, relative to the centre.
     * Used by the CIRCLE_LINE job only. */
    float line_x1, line_y1, line_x2, line_y2;
} circle_config_t;

typedef struct {
    uint16_t pan_min, pan_max, tilt_min, tilt_max;
} circle_limits_t;

typedef enum { CIRCLE_IDLE, CIRCLE_MOVE, CIRCLE_SETTLE,
               CIRCLE_RUN, CIRCLE_CLOSE, CIRCLE_POINT } circle_state_t;
typedef enum { CIRCLE_HOME, CIRCLE_DRY, CIRCLE_DRAW, CIRCLE_DOT,
               CIRCLE_SQUARE, CIRCLE_LINE } circle_job_t;

typedef struct {
    circle_config_t config;
    circle_limits_t limits;
    circle_state_t state;
    circle_job_t job;
    uint16_t pan, tilt, target_pan, target_tilt;
    uint8_t laser, timing_fault;
    uint32_t last_tick, phase_start;
} circle_draw_t;

int circle_config_valid(const circle_config_t *cfg, const circle_limits_t *limits);
int circle_line_valid(const circle_config_t *cfg, const circle_limits_t *limits);
int circle_parse_values(const char *line, const char *command, float *values, unsigned count);
int circle_parse_signed_values(const char *line, const char *command, float *values,
                               unsigned count);
void circle_position(const circle_config_t *cfg, float phase,
                     uint16_t *pan, uint16_t *tilt);
void square_position(const circle_config_t *cfg, float progress,
                     uint16_t *pan, uint16_t *tilt);
void line_position(const circle_config_t *cfg, float progress,
                   uint16_t *pan, uint16_t *tilt);
void circle_init(circle_draw_t *draw, const circle_config_t *cfg,
                 const circle_limits_t *limits);
int circle_begin(circle_draw_t *draw, circle_job_t job, uint32_t now);
void circle_stop(circle_draw_t *draw);
void circle_tick(circle_draw_t *draw, uint32_t now);

#endif
