#ifndef P0_USART3_CONFIG_H
#define P0_USART3_CONFIG_H
#include "control.h"
#include "uart_parser.h"
void usart3_init(void);
void usart3_send_status(const control_t *c, const uart_parser_t *p);
#endif
