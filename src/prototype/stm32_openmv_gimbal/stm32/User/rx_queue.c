#include "rx_queue.h"
#include <string.h>
void rx_queue_init(rx_queue_t *q) { memset(q, 0, sizeof(*q)); }
void rx_queue_push(rx_queue_t *q, uint8_t byte, uint32_t received_ms)
{
    uint8_t next = (uint8_t)((q->head + 1u) % RX_QUEUE_SIZE);
    if (q->overflow || next == q->tail) { q->overflow = 1; return; }
    q->bytes[q->head].byte = byte;
    q->bytes[q->head].received_ms = received_ms;
    q->head = next;
}
int rx_queue_pop(rx_queue_t *q, rx_byte_t *out)
{
    if (q->overflow) { q->tail = q->head; q->overflow = 0; return -1; }
    if (q->head == q->tail) return 0;
    *out = q->bytes[q->tail];
    q->tail = (uint8_t)((q->tail + 1u) % RX_QUEUE_SIZE);
    return 1;
}
