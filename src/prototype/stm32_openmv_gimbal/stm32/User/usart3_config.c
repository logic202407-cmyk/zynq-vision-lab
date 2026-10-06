#include "stm32f10x.h"
#include "usart3_config.h"
#include "usart_config.h"
#include <stdio.h>
static char tx_buf[420];
static unsigned tx_pos, tx_size;
static uint32_t tx_skipped;
#ifdef P0_LOG_ONLY
#define OUTPUTS_ENABLED 0u
#else
#define OUTPUTS_ENABLED 1u
#endif
void usart3_poll_tx(void)
{
    if (tx_pos < tx_size && USART_GetFlagStatus(USART3, USART_FLAG_TXE) != RESET)
        USART_SendData(USART3, (uint8_t)tx_buf[tx_pos++]);
}
void usart3_init(void)
{
    GPIO_InitTypeDef gpio;
    USART_InitTypeDef uart;
#ifndef P0_LOG_ONLY
    NVIC_InitTypeDef nvic;
#endif
    tx_pos = tx_size = 0;
    tx_skipped = 0;
    serial_rx_init(3);
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOB, ENABLE);
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_USART3, ENABLE);
    gpio.GPIO_Pin = GPIO_Pin_10;
    gpio.GPIO_Mode = GPIO_Mode_AF_PP;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOB, &gpio);
#ifndef P0_LOG_ONLY
    gpio.GPIO_Pin = GPIO_Pin_11;
    gpio.GPIO_Mode = GPIO_Mode_IN_FLOATING;
    GPIO_Init(GPIOB, &gpio);
#endif
    USART_StructInit(&uart);
    uart.USART_BaudRate = 115200;
#ifdef P0_LOG_ONLY
    uart.USART_Mode = USART_Mode_Tx;
#endif
    USART_Init(USART3, &uart);
#ifndef P0_LOG_ONLY
    nvic.NVIC_IRQChannel = USART3_IRQn;
    nvic.NVIC_IRQChannelPreemptionPriority = 1;
    nvic.NVIC_IRQChannelSubPriority = 1;
    nvic.NVIC_IRQChannelCmd = ENABLE;
    NVIC_Init(&nvic);
    USART_ITConfig(USART3, USART_IT_RXNE, ENABLE);
#endif
    USART_Cmd(USART3, ENABLE);
}
void usart3_send_status(const control_t *c, const uart_parser_t *p)
{
    int length;
    if (tx_pos < tx_size) { ++tx_skipped; return; }
    length = snprintf(tx_buf, sizeof(tx_buf),
        "P0V 1 STATE %s MODE %s VALID %u ENABLED %u DX %d DY %d "
        "PAN %u TLT %u REQ_PAN %u REQ_TLT %u "
        "SESSION %lu FRAME %lu RX_MS %lu SOURCE_MS %lu "
        "REJECT %s BAD %lu PARSE_BAD %lu PKP %ld PKI %ld PKD %ld TKP %ld TKI %ld TKD %ld "
        "OUTPUTS %u TX_SKIPPED %lu PARSER_REJECT %s\r\n",
        observation_name(c->state), c->manual ? "manual" : "auto", (unsigned)c->valid,
        (unsigned)c->auto_enabled, (int)c->dx, (int)c->dy, (unsigned)c->pan_us,
        (unsigned)c->tilt_us, (unsigned)c->requested_pan, (unsigned)c->requested_tilt,
        (unsigned long)c->session, (unsigned long)c->frame, (unsigned long)c->received_ms,
        (unsigned long)c->source_ms, reject_name(c->last_reject), (unsigned long)c->rejected,
        (unsigned long)p->rejected, (long)(c->pan_pid.Kp * 100), (long)(c->pan_pid.Ki * 100),
        (long)(c->pan_pid.Kd * 100), (long)(c->tilt_pid.Kp * 100),
        (long)(c->tilt_pid.Ki * 100), (long)(c->tilt_pid.Kd * 100),
        OUTPUTS_ENABLED, (unsigned long)tx_skipped, reject_name(p->last_reject));
    tx_pos = tx_size = 0;
    if (length > 0 && (unsigned)length < sizeof(tx_buf)) tx_size = (unsigned)length;
    else ++tx_skipped;
}
void USART3_IRQHandler(void) { serial_rx_interrupt(3); }
