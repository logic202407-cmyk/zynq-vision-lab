/* Host-only SPL stub. Never include this directory in a device build. */
#ifndef FIXED_CAMERA_HOST_STM32F10X_H
#define FIXED_CAMERA_HOST_STM32F10X_H
#include <stdint.h>
#include <string.h>
typedef struct { uint16_t GPIO_Pin; int GPIO_Mode; int GPIO_Speed; } GPIO_InitTypeDef;
typedef struct { uint32_t USART_BaudRate; uint16_t USART_Mode; } USART_InitTypeDef;
typedef struct { uint32_t SR, DR; } USART_TypeDef;
extern USART_TypeDef fixture_uart;
#define USART3 (&fixture_uart)
#define GPIOB ((void *)1)
#define TIM2 ((void *)2)
#define USART3_IRQn 39
#define RCC_APB2Periph_GPIOB 8U
#define RCC_APB2Periph_AFIO 1U
#define RCC_APB1Periph_USART3 0x40000U
#define GPIO_Pin_10 0x400U
#define GPIO_Pin_11 0x800U
#define GPIO_Mode_AF_PP 1
#define GPIO_Mode_IN_FLOATING 2
#define GPIO_Speed_50MHz 3
#define USART_Mode_Rx 4U
#define USART_Mode_Tx 8U
#define USART_FLAG_TXE 0x80U
#define USART_FLAG_RXNE 0x20U
#define USART_FLAG_ORE 8U
#define USART_FLAG_FE 2U
#define USART_FLAG_NE 4U
#define RESET 0
#define ENABLE 1
#define DISABLE 0
extern uint32_t SystemCoreClock;
#define NVIC_DisableIRQ(a) ((void)(a))
#define RCC_APB2PeriphClockCmd(a,b) ((void)(a), (void)(b))
#define RCC_APB1PeriphClockCmd(a,b) ((void)(a), (void)(b))
#define GPIO_Init(a,b) ((void)(a), (void)(b))
#define USART_StructInit(a) memset((a), 0, sizeof(*(a)))
#define USART_Init(a,b) ((void)(a), (void)(b))
#define USART_Cmd(a,b) ((void)(a), (void)(b))
#define TIM_UpdateDisableConfig(a,b) ((void)(a), (void)(b))
#define SysTick_Config(a) ((void)(a), 0U)
int USART_GetFlagStatus(USART_TypeDef *port, uint16_t flag);
void USART_SendData(USART_TypeDef *port, uint16_t byte);
uint16_t USART_ReceiveData(USART_TypeDef *port);
#endif
