#include "control.h"
#include "uart_parser.h"
#include "command.h"
#include "rx_queue.h"
#include <stdio.h>
#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT __attribute__((visibility("default")))
#endif
static control_t c;
static uart_parser_t p;
static command_t cmd;
static rx_queue_t queue;
EXPORT void p0_reset(void)
{
    control_init(&c); uart_parser_init(&p); command_init(&cmd); rx_queue_init(&queue);
}
EXPORT void p0_byte(unsigned byte, uint32_t received_ms, uint32_t now_ms)
{
    track_target_t t;
    uint32_t rejected = p.rejected;
    int ready = uart_parser_feed(&p, (uint8_t)byte, received_ms, &t);
    if (p.rejected != rejected) control_invalidate(&c, p.last_reject);
    if (ready) (void)control_frame(&c, &t, now_ms);
}
EXPORT void p0_tick(uint32_t now_ms)
{
    control_tick(&c, now_ms);
    if (uart_parser_expire(&p, now_ms)) control_invalidate(&c, p.last_reject);
}
EXPORT int p0_command(const char *s)
{
    int result = 0;
    while (*s) { int value = command_feed(&cmd, &c, (uint8_t)*s++); if (value) result = value; }
    return result;
}
EXPORT const char *p0_snapshot(void)
{
    static char text[1500];
    snprintf(text, sizeof(text),
        "{\"state\":\"%s\",\"mode\":\"%s\",\"valid\":%u,\"enabled\":%u,"
        "\"dx\":%d,\"dy\":%d,\"pan\":%u,\"tilt\":%u,\"requested_pan\":%u,\"requested_tilt\":%u,"
        "\"session\":%lu,\"frame\":%lu,\"rx_ms\":%lu,\"source_ms\":%lu,\"reject\":\"%s\","
        "\"parse_rejected\":%lu,\"control_rejected\":%lu,\"command_rejected\":%lu,"
        "\"filter_ready\":%u,\"filt_dx\":%.6f,\"filt_dy\":%.6f,\"raw_dx\":%.6f,\"raw_dy\":%.6f,"
        "\"pan_integral\":%.6f,\"tilt_integral\":%.6f,\"pan_prev\":%.6f,\"tilt_prev\":%.6f,"
        "\"updated\":%u,\"recoveries\":%lu,\"pkp\":%.6f,\"pki\":%.6f,\"pkd\":%.6f}",
        observation_name(c.state), c.manual ? "manual" : "auto", (unsigned)c.valid,
        (unsigned)c.auto_enabled, (int)c.dx, (int)c.dy, (unsigned)c.pan_us, (unsigned)c.tilt_us,
        (unsigned)c.requested_pan, (unsigned)c.requested_tilt, (unsigned long)c.session,
        (unsigned long)c.frame, (unsigned long)c.received_ms, (unsigned long)c.source_ms,
        reject_name(c.last_reject), (unsigned long)p.rejected, (unsigned long)c.rejected,
        (unsigned long)cmd.rejected, (unsigned)c.filter_ready, (double)c.filt_dx, (double)c.filt_dy,
        (double)c.raw_dx, (double)c.raw_dy, (double)c.pan_pid.integral, (double)c.tilt_pid.integral,
        (double)c.pan_pid.prev_error, (double)c.tilt_pid.prev_error, (unsigned)c.updated,
        (unsigned long)c.recoveries, (double)c.pan_pid.Kp, (double)c.pan_pid.Ki, (double)c.pan_pid.Kd);
    return text;
}
EXPORT void p0_queue_push(unsigned byte, uint32_t now_ms) { rx_queue_push(&queue, (uint8_t)byte, now_ms); }
EXPORT int p0_queue_pop(uint32_t *stamp, unsigned *byte)
{
    rx_byte_t out;
    int result = rx_queue_pop(&queue, &out);
    if (result == 1) { *stamp = out.received_ms; *byte = out.byte; }
    return result;
}
