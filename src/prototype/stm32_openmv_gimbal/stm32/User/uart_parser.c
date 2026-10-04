#include "uart_parser.h"
#include <string.h>

static uint16_t u16(const uint8_t *p)
{
    return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}
static uint32_t u32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static int16_t s16(const uint8_t *p)
{
    int32_t v = u16(p);
    return (int16_t)(v >= 32768 ? v - 65536 : v);
}
static uint16_t crc16(const uint8_t *p, unsigned count)
{
    uint16_t crc = 0xffffu;
    unsigned i, bit;
    for (i = 0; i < count; ++i) {
        crc ^= (uint16_t)((uint16_t)p[i] << 8);
        for (bit = 0; bit < 8; ++bit)
            crc = (uint16_t)((crc & 0x8000u) ? ((uint32_t)crc << 1) ^ 0x1021u : (uint32_t)crc << 1);
    }
    return crc;
}
static void drop_first(uart_parser_t *p)
{
    --p->used;
    memmove(p->buf, p->buf + 1, p->used);
}
static void reject(uart_parser_t *p, reject_t reason)
{
    ++p->rejected;
    p->last_reject = reason;
}
void uart_parser_init(uart_parser_t *p)
{
    memset(p, 0, sizeof(*p));
}
int uart_parser_expire(uart_parser_t *p, uint32_t now_ms)
{
    if (p->used && (uint32_t)(now_ms - p->last_byte_ms) >= P0_BYTE_TIMEOUT_MS) {
        p->used = 0;
        reject(p, REJECT_PARTIAL);
        return 1;
    }
    return 0;
}
int uart_parser_feed(uart_parser_t *p, uint8_t byte, uint32_t received_ms,
                     track_target_t *out)
{
    reject_t error;
    (void)uart_parser_expire(p, received_ms);
    p->last_byte_ms = received_ms;
    p->buf[p->used++] = byte;
    /* Sliding resynchronization retains headers inside a rejected candidate. */
    while (p->used) {
        if (p->buf[0] != 0xaa) { drop_first(p); continue; }
        if (p->used == 1) break;
        if (p->buf[1] != 0x55) { drop_first(p); continue; }
        if (p->used < P0_PACKET_SIZE) break;
        error = REJECT_NONE;
        if (p->buf[3] != P0_PACKET_SIZE) error = REJECT_LENGTH;
        else if (p->buf[2] != 1) error = REJECT_VERSION;
        else if (p->buf[24] != 0x0d || p->buf[25] != 0x0a) error = REJECT_TAIL;
        else if (crc16(p->buf + 2, 20) != u16(p->buf + 22)) error = REJECT_CRC;
        else if (p->buf[4] > 1) error = REJECT_FLAGS;
        else if (p->buf[5] != 1) error = REJECT_CONFIG;
        else if (!u32(p->buf + 6)) error = REJECT_FIELDS;
        else if (s16(p->buf + 18) < -80 || s16(p->buf + 18) > 80 ||
                 s16(p->buf + 20) < -60 || s16(p->buf + 20) > 60) error = REJECT_RANGE;
        else if (!p->buf[4] && (s16(p->buf + 18) || s16(p->buf + 20))) error = REJECT_FIELDS;
        if (error != REJECT_NONE) {
            reject(p, error);
            drop_first(p);
            continue;
        }
        out->valid = p->buf[4];
        out->config = p->buf[5];
        out->session = u32(p->buf + 6);
        out->frame = u32(p->buf + 10);
        out->source_ms = u32(p->buf + 14);
        out->dx = s16(p->buf + 18);
        out->dy = s16(p->buf + 20);
        out->received_ms = received_ms;
        ++p->total_frames;
        p->used = 0;
        return 1;
    }
    return 0;
}
const char *reject_name(reject_t reason)
{
    static const char *const names[] = {
        "none", "length", "version", "crc", "tail", "flags", "config", "range",
        "fields", "partial", "session", "frame", "stale", "command", "overflow"
    };
    return names[(unsigned)reason < sizeof(names) / sizeof(names[0]) ? reason : REJECT_FIELDS];
}
