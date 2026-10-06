#ifndef P0_UART_PARSER_H
#define P0_UART_PARSER_H
#include <stdint.h>

/* Independent temporary wire format stm32-p0/v1; NOT a team protocol. */
#define P0_PACKET_SIZE 26u
#define P0_BYTE_TIMEOUT_MS 20u
typedef enum {
    REJECT_NONE, REJECT_LENGTH, REJECT_VERSION, REJECT_CRC, REJECT_TAIL,
    REJECT_FLAGS, REJECT_CONFIG, REJECT_RANGE, REJECT_FIELDS,
    REJECT_PARTIAL, REJECT_SESSION, REJECT_FRAME, REJECT_STALE,
    REJECT_COMMAND, REJECT_OVERFLOW
} reject_t;
typedef struct {
    uint32_t session, frame, source_ms, received_ms;
    int16_t dx, dy;
    uint8_t valid, config;
} track_target_t;
typedef struct {
    uint8_t buf[P0_PACKET_SIZE], used;
    uint32_t last_byte_ms, total_frames, rejected;
    reject_t last_reject;
} uart_parser_t;
void uart_parser_init(uart_parser_t *p);
int uart_parser_feed(uart_parser_t *p, uint8_t byte, uint32_t received_ms,
                     track_target_t *out);
int uart_parser_expire(uart_parser_t *p, uint32_t now_ms);
const char *reject_name(reject_t reason);
#endif
