#ifndef P0_RX_QUEUE_H
#define P0_RX_QUEUE_H
#include <stdint.h>
#define RX_QUEUE_SIZE 128u
typedef struct { uint32_t received_ms; uint8_t byte; } rx_byte_t;
typedef struct {
    rx_byte_t bytes[RX_QUEUE_SIZE];
    volatile uint8_t head, tail, overflow;
} rx_queue_t;
void rx_queue_init(rx_queue_t *q);
void rx_queue_push(rx_queue_t *q, uint8_t byte, uint32_t received_ms);
/* Caller excludes producer interrupts during pop; -1 flushes overflow. */
int rx_queue_pop(rx_queue_t *q, rx_byte_t *out);
#endif
