/**
 * @file    stm32f10x_it.c
 * @brief   Interrupt service routines
 * @note    USART1_IRQHandler is implemented in usart_config.c
 */

#include "stm32f10x_it.h"
#include "laser.h"

extern volatile uint32_t g_ms_tick;

/******************************************************************************/
/*            Cortex-M3 Processor Exceptions Handlers                         */
/******************************************************************************/

void NMI_Handler(void)           { laser_off(); while (1); }
void HardFault_Handler(void)     { laser_off(); while (1); }
void MemManage_Handler(void)     { laser_off(); while (1); }
void BusFault_Handler(void)      { laser_off(); while (1); }
void UsageFault_Handler(void)    { laser_off(); while (1); }
void SVC_Handler(void)           { }
void DebugMon_Handler(void)      { }
void PendSV_Handler(void)        { }
void SysTick_Handler(void)       { g_ms_tick++; }
