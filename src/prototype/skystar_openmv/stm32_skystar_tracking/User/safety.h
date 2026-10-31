#ifndef SKYSTAR_SAFETY_H
#define SKYSTAR_SAFETY_H
#include "tracking.h"
#define SAFETY_LEASE_MS 500u
#define SAFETY_COMMAND_MS 200u
#define SAFETY_LINE_BYTES 96u
typedef enum { SAFE_STOPPED, SAFE_ARMED, SAFE_MANUAL, SAFE_AUTO, SAFE_FAULT } safe_state_t;
typedef enum {
    SAFE_BOOT, SAFE_STOP, SAFE_READY, SAFE_LINK_TIMEOUT, SAFE_STALE,
    SAFE_PARSE, SAFE_UART, SAFE_KEY, SAFE_VISION, SAFE_ENTROPY
} safe_reason_t;
typedef struct {
    safe_state_t state;
    safe_reason_t reason;
    uint32_t nonce_hi, nonce_lo, sequence, live_ms, mode_ms, rejected;
    uint8_t entropy_ok;
    const char *last_reject;
} safety_t;
void safety_init(safety_t *s, uint32_t hi, uint32_t lo, int entropy_ok);
int safety_armed(const safety_t *s);
void safety_trip(safety_t *s, tracking_t *c, safe_reason_t reason);
void safety_tick(safety_t *s, tracking_t *c, uint32_t now);
int safety_command(safety_t *s, tracking_t *c, const char *line, uint32_t rx, uint32_t now);
uint16_t safety_crc(const char *data, unsigned count);
const char *safety_state_name(const safety_t *s);
const char *safety_reason_name(const safety_t *s);
#endif
