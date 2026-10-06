#ifndef LOG_TEST_STM32F10X_H
#define LOG_TEST_STM32F10X_H
#include <stdint.h>
#define USART3 3u
#define GPIOB 2u
#define RESET 0u
#define SET 1u
#define ENABLE 1u
#define USART_FLAG_TXE 128u
#define USART_IT_RXNE 32u
#define USART_Mode_Tx 8u
#define GPIO_Pin_10 1024u
#define GPIO_Pin_11 2048u
#define GPIO_Mode_AF_PP 2u
#define GPIO_Mode_IN_FLOATING 1u
#define GPIO_Speed_50MHz 3u
#define RCC_APB2Periph_GPIOB 8u
#define RCC_APB1Periph_USART3 0x40000u
#define USART3_IRQn 39u
typedef struct { unsigned GPIO_Pin, GPIO_Mode, GPIO_Speed; } GPIO_InitTypeDef;
typedef struct { unsigned USART_BaudRate, USART_Mode; } USART_InitTypeDef;
typedef struct {
    unsigned NVIC_IRQChannel, NVIC_IRQChannelPreemptionPriority;
    unsigned NVIC_IRQChannelSubPriority, NVIC_IRQChannelCmd;
} NVIC_InitTypeDef;
extern uint32_t SystemCoreClock;
unsigned SysTick_Config(uint32_t ticks);
unsigned USART_GetFlagStatus(unsigned uart, unsigned flag);
void USART_SendData(unsigned uart, uint16_t value);
void RCC_APB2PeriphClockCmd(unsigned clocks, unsigned enable);
void RCC_APB1PeriphClockCmd(unsigned clocks, unsigned enable);
void GPIO_Init(unsigned gpio, const GPIO_InitTypeDef *config);
void USART_StructInit(USART_InitTypeDef *config);
void USART_Init(unsigned uart, const USART_InitTypeDef *config);
void NVIC_Init(const NVIC_InitTypeDef *config);
void USART_ITConfig(unsigned uart, unsigned interrupt, unsigned enable);
void USART_Cmd(unsigned uart, unsigned enable);
#endif
