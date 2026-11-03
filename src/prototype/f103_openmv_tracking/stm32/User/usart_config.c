/**
 * @file    usart_config.c
 * @brief   USART1 初始化 + RX 中断服务函数
 * @note    STM32F103C8T6, PA10=USART1_RX, 115200-8N1
 *          接线: OpenMV P4(TX) → STM32 PA10(RX), 共地
 */

#include "stm32f10x.h"
#include "uart_parser.h"
#include "laser.h"
extern volatile uint32_t g_ms_tick;

/* ===== 全局解析器 (main.c 引用) ===== */
uart_parser_t g_parser;

/**
 * @brief  USART1 初始化
 *         PA9  = TX (复用推挽, 备用)
 *         PA10 = RX (浮空输入)
 *         波特率 115200, 8N1, RX 中断使能
 */
void usart1_init(void)
{
    GPIO_InitTypeDef  gpio;
    USART_InitTypeDef usart;
    NVIC_InitTypeDef  nvic;

    /* 时钟: USART1 + GPIOA + AFIO */
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_USART1
                         | RCC_APB2Periph_GPIOA
                         | RCC_APB2Periph_AFIO, ENABLE);

    /* PA9  = USART1_TX (复用推挽) */
    gpio.GPIO_Pin   = GPIO_Pin_9;
    gpio.GPIO_Mode  = GPIO_Mode_AF_PP;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOA, &gpio);

    /* PA10 = USART1_RX (浮空输入) */
    gpio.GPIO_Pin  = GPIO_Pin_10;
    gpio.GPIO_Mode = GPIO_Mode_IN_FLOATING;
    GPIO_Init(GPIOA, &gpio);

    /* USART1: 115200, 8N1 */
    usart.USART_BaudRate            = 115200;
    usart.USART_WordLength          = USART_WordLength_8b;
    usart.USART_StopBits            = USART_StopBits_1;
    usart.USART_Parity              = USART_Parity_No;
    usart.USART_HardwareFlowControl = USART_HardwareFlowControl_None;
    usart.USART_Mode                = USART_Mode_Rx | USART_Mode_Tx;
    USART_Init(USART1, &usart);

    /* RXNE 中断使能 */
    USART_ITConfig(USART1, USART_IT_RXNE, ENABLE);

    /* NVIC */
    nvic.NVIC_IRQChannel                   = USART1_IRQn;
    nvic.NVIC_IRQChannelPreemptionPriority = 1;
    nvic.NVIC_IRQChannelSubPriority        = 0;
    nvic.NVIC_IRQChannelCmd                = ENABLE;
    NVIC_Init(&nvic);

    /* 初始化解析器 */
    uart_parser_init(&g_parser);
    USART_Cmd(USART1, ENABLE);
}

/**
 * @brief  USART1 中断 — 逐字节喂入状态机
 */
void USART1_IRQHandler(void)
{
    uint32_t sr = USART1->SR;
    if (sr & (USART_SR_ORE | USART_SR_FE | USART_SR_NE | USART_SR_PE)) {
        (void)USART1->DR;
        uart_parser_fault(&g_parser);
        laser_off();
    } else if (sr & USART_SR_RXNE) {
        uart_parser_feed(&g_parser, (uint8_t)USART1->DR, g_ms_tick);
    }
}
