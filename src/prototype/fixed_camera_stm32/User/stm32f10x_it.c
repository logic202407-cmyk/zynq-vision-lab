#include "stm32f10x.h"

extern volatile uint32_t g_ms_tick;

static void fault_stop(void)
{
    __disable_irq();
    /* Force PA4 low without relying on a potentially stale software flag.
     * This also handles a fault before laser_init() configures the pin. */
    RCC->APB2ENR |= RCC_APB2ENR_IOPAEN;
    GPIOA->BRR = GPIO_Pin_4;
    GPIOA->CRL = (GPIOA->CRL & ~(0xFUL << 16)) | (0x2UL << 16);
    for (;;) { }
}

void NMI_Handler(void)       { fault_stop(); }
void HardFault_Handler(void) { fault_stop(); }
void MemManage_Handler(void) { fault_stop(); }
void BusFault_Handler(void)  { fault_stop(); }
void UsageFault_Handler(void){ fault_stop(); }
void SVC_Handler(void)       { }
void DebugMon_Handler(void)  { }
void PendSV_Handler(void)    { }
void SysTick_Handler(void)   { ++g_ms_tick; }
