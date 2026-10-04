#include "stm32f10x.h"
#include "usart_config.h"
extern volatile uint32_t g_ms_tick;
static rx_queue_t queues[2];
void serial_rx_init(unsigned port) { rx_queue_init(&queues[port == 3]); }
int serial_rx_pop(unsigned port, rx_byte_t *out)
{
    uint32_t saved = __get_PRIMASK();
    int result;
    __disable_irq();
    result = rx_queue_pop(&queues[port == 3], out);
    __set_PRIMASK(saved);
    return result;
}
void serial_rx_interrupt(unsigned port)
{
    USART_TypeDef *uart = port == 3 ? USART3 : USART1;
    rx_queue_t *q = &queues[port == 3];
    uint32_t sr = uart->SR;
    if (sr & (USART_FLAG_RXNE | USART_FLAG_ORE | USART_FLAG_NE | USART_FLAG_FE | USART_FLAG_PE)) {
        uint8_t byte = (uint8_t)uart->DR;
        if (sr & (USART_FLAG_ORE | USART_FLAG_NE | USART_FLAG_FE | USART_FLAG_PE)) q->overflow = 1;
        else if (sr & USART_FLAG_RXNE) rx_queue_push(q, byte, g_ms_tick);
    }
}
void usart1_init(void)
{
    GPIO_InitTypeDef gpio;
    USART_InitTypeDef uart;
    NVIC_InitTypeDef nvic;
    serial_rx_init(1);
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_USART1 | RCC_APB2Periph_GPIOA, ENABLE);
    gpio.GPIO_Pin = GPIO_Pin_9;
    gpio.GPIO_Mode = GPIO_Mode_AF_PP;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOA, &gpio);
    gpio.GPIO_Pin = GPIO_Pin_10;
    gpio.GPIO_Mode = GPIO_Mode_IN_FLOATING;
    GPIO_Init(GPIOA, &gpio);
    USART_StructInit(&uart);
    uart.USART_BaudRate = 115200;
    USART_Init(USART1, &uart);
    nvic.NVIC_IRQChannel = USART1_IRQn;
    nvic.NVIC_IRQChannelPreemptionPriority = 1;
    nvic.NVIC_IRQChannelSubPriority = 0;
    nvic.NVIC_IRQChannelCmd = ENABLE;
    NVIC_Init(&nvic);
    USART_ITConfig(USART1, USART_IT_RXNE, ENABLE);
    USART_Cmd(USART1, ENABLE);
}
void USART1_IRQHandler(void) { serial_rx_interrupt(1); }
