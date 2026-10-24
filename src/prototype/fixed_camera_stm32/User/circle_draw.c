#include "circle_draw.h"
#include <math.h>
#include <string.h>

#define TWO_PI 6.2831853071795864769f
#define SEAM_PHASE (TWO_PI - 0.0001f)
#define BACK_MAX 100U
#define STEP_MS 20U
#define STEP_US 2U
#define SETTLE_MS 500U
#define DOT_MS 300U
#define CLOSE_MS 200U

/* Bounded decimal parameters; avoid floating scanf's large M3 stack use.
 * allow_sign lets the stroke endpoints go negative; every other command keeps
 * the strict unsigned grammar so malformed input is rejected at parse time. */
static int parse_values(const char *line, const char *command, float *values,
                        unsigned count, int allow_sign)
{
    unsigned i, digits;
    size_t length = strlen(command);
    const char *p;
    float value, fraction, sign;
    if (strncmp(line, command, length) != 0) return 0;
    p = line + length;
    if (*p != ' ' && *p != '\t') return 0;
    for (i = 0; i < count; i++) {
        while (*p == ' ' || *p == '\t') p++;
        sign = 1.0f;
        if (allow_sign && *p == '-') { sign = -1.0f; p++; }
        if (*p < '0' || *p > '9') return 0;
        value = 0.0f; digits = 0;
        while (*p >= '0' && *p <= '9') {
            if (++digits > 8U) return 0;
            value = value * 10.0f + (*p++ - '0');
        }
        if (*p == '.') {
            p++; fraction = 0.1f;
            while (*p >= '0' && *p <= '9') {
                if (++digits > 8U) return 0;
                value += (*p++ - '0') * fraction;
                fraction *= 0.1f;
            }
        }
        if (*p && *p != ' ' && *p != '\t') return 0;
        values[i] = sign * value;
    }
    while (*p == ' ' || *p == '\t') p++;
    return *p == '\0';
}

int circle_parse_values(const char *line, const char *command, float *values, unsigned count)
{
    return parse_values(line, command, values, count, 0);
}

int circle_parse_signed_values(const char *line, const char *command, float *values,
                               unsigned count)
{
    return parse_values(line, command, values, count, 1);
}

int circle_config_valid(const circle_config_t *c, const circle_limits_t *l)
{
    float pan_span, tilt_span;
    /* Comparisons also reject NaN/Inf. The 0.35 limit keeps the whole lap inside
     * a 38 deg sweep: wide enough for a 200-300 mm circle on paper, still inside
     * the servo travel measured on the bench. */
    if (!(c->distance_mm >= 300.0f && c->distance_mm <= 2000.0f
       && c->radius_mm >= 5.0f && c->radius_mm <= 150.0f
       && c->radius_mm <= 0.35f * c->distance_mm
       && c->pan_us_per_rad >= 100.0f && c->pan_us_per_rad <= 1700.0f
       && c->tilt_us_per_rad >= 150.0f && c->tilt_us_per_rad <= 2600.0f
       && c->pan_back_us <= BACK_MAX && c->tilt_back_us <= BACK_MAX)
       || c->period_ms < 3000U || c->period_ms > 30000U) return 0;
    /* The lead rides on top of the geometric span, so it has to fit as well. */
    pan_span = atanf(c->radius_mm / c->distance_mm) * c->pan_us_per_rad
             + (float)c->pan_back_us;
    tilt_span = atanf(c->radius_mm / c->distance_mm) * c->tilt_us_per_rad
              + (float)c->tilt_back_us;
    /* Reject the WHOLE path instead of silently clipping it into another shape. */
    return c->center_pan - pan_span >= l->pan_min
        && c->center_pan + pan_span <= l->pan_max
        && c->center_tilt - tilt_span >= l->tilt_min
        && c->center_tilt + tilt_span <= l->tilt_max;
}

static int sign_of(float value)
{
    return (value > 0.0f) - (value < 0.0f);
}

/* Shared projection: paper coordinates -> pulse widths, plus the dead-band lead
 * that each axis needs while it travels in pan_dir / tilt_dir (-1, 0, +1). */
static void project(const circle_config_t *c, float x, float y,
                    int pan_dir, int tilt_dir, uint16_t *pan, uint16_t *tilt)
{
    float yaw = atan2f(x, c->distance_mm);
    float pitch = atan2f(y, sqrtf(c->distance_mm * c->distance_mm + x * x));
    float pan_us = c->center_pan + yaw * c->pan_us_per_rad;
    float tilt_us = c->center_tilt + pitch * c->tilt_us_per_rad;

    /* Ideal intersecting axes, paper perpendicular to the centre beam.
     * Side mounting / gear backlash / actual servo gain need physical calibration. */
    pan_us += (float)(pan_dir * (int)c->pan_back_us);
    tilt_us += (float)(tilt_dir * (int)c->tilt_back_us);
    *pan = (uint16_t)(pan_us + 0.5f);
    *tilt = (uint16_t)(tilt_us + 0.5f);
}

void circle_position(const circle_config_t *c, float phase,
                     uint16_t *pan, uint16_t *tilt)
{
    float x = c->radius_mm * cosf(phase);
    float y = c->radius_mm * sinf(phase);
    /* d(x)/d(phase) = -sin, d(y)/d(phase) = cos: the lead follows the travel. */
    project(c, x, y, sign_of(-sinf(phase)), sign_of(cosf(phase)), pan, tilt);
}

/* Square lap in paper coordinates: radius_mm is the HALF SIDE.  The lap starts
 * at the middle of the top edge so the seam has the same direction on both
 * sides of it; each edge is a single-axis move, which is what makes this shape
 * a direct readout of each axis on its own. */
#define SQ_SEAM 0.0f
void square_position(const circle_config_t *c, float progress,
                     uint16_t *pan, uint16_t *tilt)
{
    const float h = c->radius_mm;
    float x, y;
    int pan_dir = 0, tilt_dir = 0;
    if (progress >= 1.0f) {
        x = 0.0f; y = h; pan_dir = -1;              /* seam point, same as progress 0 */
    } else if (progress < 0.125f) {
        x = -8.0f * h * progress; y = h; pan_dir = -1;
    } else if (progress < 0.375f) {
        x = -h; y = h - 8.0f * h * (progress - 0.125f); tilt_dir = -1;
    } else if (progress < 0.625f) {
        x = -h + 8.0f * h * (progress - 0.375f); y = -h; pan_dir = 1;
    } else if (progress < 0.875f) {
        x = h; y = -h + 8.0f * h * (progress - 0.625f); tilt_dir = 1;
    } else {
        x = h - 8.0f * h * (progress - 0.875f); y = h; pan_dir = -1;
    }
    project(c, x, y, pan_dir, tilt_dir, pan, tilt);
}

/* Single stroke: straight line in paper millimetres from (x1,y1) to (x2,y2).
 * Speed is fixed so a short letter stroke is not drawn at a crawl. */
#define LINE_SPEED_MM_S 30.0f
#define LINE_MIN_MS 800U
#define LINE_MAX_MS 8000U

void line_position(const circle_config_t *c, float progress,
                   uint16_t *pan, uint16_t *tilt)
{
    float dx = c->line_x2 - c->line_x1;
    float dy = c->line_y2 - c->line_y1;
    float x = c->line_x1 + dx * progress;
    float y = c->line_y1 + dy * progress;
    project(c, x, y, sign_of(dx), sign_of(dy), pan, tilt);
}

static uint32_t line_duration_ms(const circle_config_t *c)
{
    float dx = c->line_x2 - c->line_x1;
    float dy = c->line_y2 - c->line_y1;
    float ms = sqrtf(dx * dx + dy * dy) * (1000.0f / LINE_SPEED_MM_S);
    if (ms < (float)LINE_MIN_MS) return LINE_MIN_MS;
    if (ms > (float)LINE_MAX_MS) return LINE_MAX_MS;
    return (uint32_t)(ms + 0.5f);
}

/* Pan is monotonic along a line. Pitch can also have one interior extremum,
 * since its derivative has numerator A + B*t. Check that point and both ends
 * using exactly the signed lead used by line_position(), before integer casts. */
int circle_line_valid(const circle_config_t *c, const circle_limits_t *l)
{
    float cone, dx, dy, a, b;
    float x[3], y[3];
    unsigned i, count = 2U;
    if (!circle_config_valid(c, l)) return 0;
    cone = 0.35f * c->distance_mm;
    x[0] = c->line_x1; y[0] = c->line_y1;
    x[1] = c->line_x2; y[1] = c->line_y2;
    for (i = 0; i < 2U; i++) {
        /* Ordered finite bounds also reject NaN and infinity. The cone is
         * convex, so bounded endpoints keep the entire segment inside it. */
        if (!(x[i] >= -cone && x[i] <= cone && y[i] >= -cone && y[i] <= cone)) return 0;
    }
    dx = x[1] - x[0]; dy = y[1] - y[0];
    a = dy * (c->distance_mm * c->distance_mm + x[0] * x[0])
      - y[0] * x[0] * dx;
    b = dy * x[0] * dx - y[0] * dx * dx;
    if (b != 0.0f) {
        float t = -a / b;
        if (t > 0.0f && t < 1.0f) {
            x[count] = x[0] + dx * t;
            y[count] = y[0] + dy * t;
            count++;
        }
    }
    for (i = 0; i < count; i++) {
        float yaw, pitch, pan, tilt;
        yaw = atan2f(x[i], c->distance_mm);
        pitch = atan2f(y[i], sqrtf(c->distance_mm * c->distance_mm + x[i] * x[i]));
        pan = c->center_pan + yaw * c->pan_us_per_rad
            + (float)(sign_of(dx) * (int)c->pan_back_us);
        tilt = c->center_tilt + pitch * c->tilt_us_per_rad
             + (float)(sign_of(dy) * (int)c->tilt_back_us);
        if (!(pan >= l->pan_min && pan <= l->pan_max)) return 0;
        if (!(tilt >= l->tilt_min && tilt <= l->tilt_max)) return 0;
    }
    return 1;
}

void circle_init(circle_draw_t *d, const circle_config_t *c, const circle_limits_t *l)
{
    memset(d, 0, sizeof(*d));
    d->config = *c;
    d->limits = *l;
    d->pan = c->center_pan;
    d->tilt = c->center_tilt;
}

void circle_stop(circle_draw_t *d)
{
    d->laser = 0;
    d->state = CIRCLE_IDLE; /* Hold the last commanded position, no lit return line. */
}

int circle_begin(circle_draw_t *d, circle_job_t job, uint32_t now)
{
    if (d->state != CIRCLE_IDLE || !circle_config_valid(&d->config, &d->limits)) return 0;
    if (job == CIRCLE_LINE && !circle_line_valid(&d->config, &d->limits)) return 0;
    d->job = job;
    d->laser = 0;
    d->timing_fault = 0;
    d->last_tick = now;
    if (job == CIRCLE_LINE) {
        line_position(&d->config, 0.0f, &d->target_pan, &d->target_tilt);
    } else if (job == CIRCLE_SQUARE) {
        square_position(&d->config, 0.0f, &d->target_pan, &d->target_tilt);
    } else if (job == CIRCLE_DRY || job == CIRCLE_DRAW) {
        circle_position(&d->config, 0.0f, &d->target_pan, &d->target_tilt);
    } else {
        d->target_pan = d->config.center_pan;
        d->target_tilt = d->config.center_tilt;
    }
    d->state = CIRCLE_MOVE;
    return 1;
}

static uint16_t approach(uint16_t current, uint16_t target)
{
    if (target > current && (unsigned)(target - current) > STEP_US) return current + STEP_US;
    if (current > target && (unsigned)(current - target) > STEP_US) return current - STEP_US;
    return target;
}

void circle_tick(circle_draw_t *d, uint32_t now)
{
    uint32_t elapsed;
    if (d->state == CIRCLE_IDLE) return;
    elapsed = (uint32_t)(now - d->last_tick);
    if (elapsed > 200U) {
        circle_stop(d);
        d->timing_fault = 1; /* Do not jump ahead after a stalled control loop. */
        return;
    }
    if (elapsed < STEP_MS) return;
    d->last_tick = now;
    switch (d->state) {
    case CIRCLE_MOVE:
        d->pan = approach(d->pan, d->target_pan);
        d->tilt = approach(d->tilt, d->target_tilt);
        if (d->pan == d->target_pan && d->tilt == d->target_tilt) {
            d->state = CIRCLE_SETTLE;
            d->phase_start = now;
        }
        break;
    case CIRCLE_SETTLE:
        if ((uint32_t)(now - d->phase_start) < SETTLE_MS) break;
        d->phase_start = now;
        if (d->job == CIRCLE_HOME) circle_stop(d);
        else if (d->job == CIRCLE_DOT) {
            d->state = CIRCLE_POINT;
            d->laser = 1;
        } else {
            d->state = CIRCLE_RUN;
            d->laser = (d->job == CIRCLE_DRAW || d->job == CIRCLE_SQUARE
                     || d->job == CIRCLE_LINE);
        }
        break;
    case CIRCLE_RUN:
        elapsed = (uint32_t)(now - d->phase_start);
        if (d->job == CIRCLE_LINE) {
            uint32_t total = line_duration_ms(&d->config);
            if (elapsed >= total) {
                line_position(&d->config, 1.0f, &d->pan, &d->tilt);
                d->state = CIRCLE_CLOSE;
                d->phase_start = now;
            } else {
                line_position(&d->config, (float)elapsed / (float)total,
                              &d->pan, &d->tilt);
            }
            break;
        }
        if (elapsed >= d->config.period_ms) {
            /* Stop an instant before the seam so the seam keeps the lead the
             * lap arrived with; backing off to the bare point would let the dead
             * band drag the lit spot away from the start mark. */
            if (d->job == CIRCLE_SQUARE) {
                square_position(&d->config, 1.0f, &d->pan, &d->tilt);
            } else {
                circle_position(&d->config, SEAM_PHASE, &d->pan, &d->tilt);
            }
            d->state = CIRCLE_CLOSE;
            d->phase_start = now;
        } else if (d->job == CIRCLE_SQUARE) {
            square_position(&d->config, (float)elapsed / (float)d->config.period_ms,
                            &d->pan, &d->tilt);
        } else {
            circle_position(&d->config, TWO_PI * elapsed / d->config.period_ms,
                            &d->pan, &d->tilt);
        }
        break;
    case CIRCLE_CLOSE:
        if ((uint32_t)(now - d->phase_start) >= CLOSE_MS) circle_stop(d);
        break;
    case CIRCLE_POINT:
        if ((uint32_t)(now - d->phase_start) >= DOT_MS) circle_stop(d);
        break;
    default:
        circle_stop(d);
        break;
    }
}
