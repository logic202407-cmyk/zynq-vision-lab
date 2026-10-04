#ifndef P0_USART_CONFIG_H
#define P0_USART_CONFIG_H
#include "rx_queue.h"
void usart1_init(void);
void serial_rx_init(unsigned port);
int serial_rx_pop(unsigned port, rx_byte_t *out);
void serial_rx_interrupt(unsigned port);
#endif
