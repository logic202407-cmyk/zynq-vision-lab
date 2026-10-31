/* STM32F407 register map checked against ST cmsis-device-f4/stm32f407xx.h.
 * HSI 16MHz baseline: no assumption about the board's external crystal.
 * Only PD12/PD13 are PWM outputs. PD14/PD15 remain low.
 */
#include "board.h"
#include "safety.h"
#include <string.h>
#ifdef BOARD_HOST_TEST
extern uint32_t *board_test_register(uint32_t address);
#define R(a) (*board_test_register(a))
#define __schedule_barrier() ((void)0)
#define __disable_irq() ((void)0)
#define __enable_irq() ((void)0)
#else
#define R(a) (*(volatile uint32_t *)(a))
#endif
#define RCC 0x40023800u
#define GPIOA 0x40020000u
#define GPIOC 0x40020800u
#define GPIOD 0x40020C00u
#define TIM4 0x40000800u
#define U1 0x40011000u
#define U2 0x40004400u
#define U3 0x40004800u
#if CONSOLE_USART == 3
#define CONSOLE U3
#else
#define CONSOLE U1
#endif
#define QSIZE 256u
typedef struct {
    volatile uint16_t head, tail;
    uint8_t bytes[QSIZE];
    uint32_t times[QSIZE];
} rx_queue_t;
static rx_queue_t vision, pc;
static volatile uint32_t milliseconds;
static volatile uint8_t fault;
static char tx[512];
static uint16_t tx_head, tx_tail;
static int pwm_enabled;
static volatile uint8_t guard_active, guard_event;
static volatile uint32_t guard_received;

static void pin(uint32_t gpio, unsigned n, unsigned mode, unsigned af)
{
    R(gpio) = (R(gpio) & ~(3u << (2*n))) | (mode << (2*n));
    R(gpio+4) &= ~(1u << n); /* push-pull */
    R(gpio+8) = (R(gpio+8) & ~(3u << (2*n))) | (1u << (2*n));
    R(gpio+0x0C) &= ~(3u << (2*n));
    if (mode == 2) {
        uint32_t address = gpio+0x20+4*(n/8);
        R(address) = (R(address) & ~(15u << (4*(n%8)))) | (af << (4*(n%8)));
    }
}
void board_init(void)
{
    volatile uint32_t dummy;
    guard_active=guard_event=fault=0; pwm_enabled=0;
    milliseconds=0; vision.head=vision.tail=pc.head=pc.tail=0;
    tx_head=tx_tail=0;
    R(0xE000ED08u)=0x08000000u;
    R(RCC) |= 1u;
    while (!(R(RCC)&2u)) { }
    R(RCC+8) &= ~3u;
    while (R(RCC+8)&12u) { }
    R(RCC+8) &= ~((15u<<4)|(7u<<10)|(7u<<13)); /* AHB/APB = HSI */
    R(RCC+0x30) |= (1u<<0)|(1u<<3);
#if CONSOLE_USART == 3
    R(RCC+0x30) |= 1u<<2;
    R(RCC+0x40) |= 1u<<18;
#endif
    R(RCC+0x40) |= (1u<<2)|(1u<<17);
    R(RCC+0x44) |= 1u<<4;
    dummy=R(RCC+0x44); dummy=R(RCC+0x40); (void)dummy;
    /* Reset only peripherals owned by this image, after clock readback. */
#if CONSOLE_USART == 3
    R(RCC+0x20) |= 1u<<18; R(RCC+0x20) &= ~(1u<<18);
#endif
    R(RCC+0x20) |= (1u<<2)|(1u<<17);
    R(RCC+0x20) &= ~((1u<<2)|(1u<<17));
    R(RCC+0x24) |= 1u<<4; R(RCC+0x24) &= ~(1u<<4);
    R(GPIOD+0x18) = 15u<<28; /* PD12..15 low before output mode */
    pin(GPIOD,12,1,0); pin(GPIOD,13,1,0);
    pin(GPIOD,14,1,0); pin(GPIOD,15,1,0);
    pin(GPIOA,0,0,0); R(GPIOA+0x0C) |= 2u; /* WKUP active high */
    pin(GPIOA,3,2,7); R(GPIOA+0x0C) |= 1u<<6; /* USART2 RX pull-up */
#if CONSOLE_USART == 3
    pin(GPIOC,10,2,7); pin(GPIOC,11,2,7);
    R(GPIOC+0x0C) |= 1u<<22;
#else
    pin(GPIOA,9,2,7); pin(GPIOA,10,2,7);
    R(GPIOA+0x0C) |= 1u<<20;
#endif
    R(CONSOLE+8)=139; R(U2+8)=139; /* 16MHz / 115200, oversampling 16 */
    R(CONSOLE+0x0C)=(1u<<13)|(1u<<5)|(1u<<3)|(1u<<2);
    R(U2+0x0C)=(1u<<13)|(1u<<5)|(1u<<2);
#if CONSOLE_USART == 3
    R(0xE000E104u)=(1u<<6)|(1u<<7); /* IRQ 38,39 */
#else
    R(0xE000E104u)=(1u<<5)|(1u<<6); /* IRQ 37,38 */
#endif
    R(TIM4+0x28)=15; R(TIM4+0x2C)=19999;
    R(TIM4+0x18)=(6u<<4)|(1u<<3)|(6u<<12)|(1u<<11);
    R(TIM4+0x20)=0;
    R(TIM4+0x34)=1500; R(TIM4+0x38)=1500;
    R(TIM4+0x14)=1; R(TIM4)= (1u<<7)|1u;
    R(0xE000E014u)=15999; R(0xE000E018u)=0; R(0xE000E010u)=7;
}
static void force_off(void)
{
    R(TIM4+0x20)=0;
    R(GPIOD+0x18)=3u<<28;
    pin(GPIOD,12,1,0); pin(GPIOD,13,1,0); pwm_enabled=0;
}
static void guard_fail(unsigned event)
{
    guard_active=0;
    if (!guard_event) guard_event=(uint8_t)event;
    force_off();
}
void SysTick_Handler(void)
{
    ++milliseconds;
    if (board_button()) guard_fail(BOARD_GUARD_KEY);
    else if (guard_active && (uint32_t)(milliseconds-guard_received)>=SAFETY_LEASE_MS)
        guard_fail(BOARD_GUARD_LEASE);
}
uint32_t board_ms(void) { return milliseconds; }
static void receive(uint32_t uart, rx_queue_t *q)
{
    uint32_t status=R(uart);
    if (status & ((1u<<5)|15u)) {
        uint8_t byte=(uint8_t)R(uart+4);
        uint16_t next=(uint16_t)((q->head+1)&255u);
        if ((status&15u) || next==q->tail) {
            fault=1; guard_fail(BOARD_GUARD_UART); return;
        }
        q->bytes[q->head]=byte; q->times[q->head]=milliseconds;
        __schedule_barrier();
        q->head=next;
    }
}
void USART1_IRQHandler(void) {
#if CONSOLE_USART == 1
    receive(U1,&pc);
#endif
}
void USART3_IRQHandler(void) {
#if CONSOLE_USART == 3
    receive(U3,&pc);
#endif
}
void USART2_IRQHandler(void) { receive(U2,&vision); }
static int pop(rx_queue_t *q, uint8_t *byte, uint32_t *time)
{
    uint16_t tail=q->tail;
    if (tail==q->head) return 0;
    __schedule_barrier();
    *byte=q->bytes[tail]; *time=q->times[tail];
    __schedule_barrier();
    q->tail=(uint16_t)((tail+1)&255u); return 1;
}
int board_vision_byte(uint8_t *byte, uint32_t *received) { return pop(&vision,byte,received); }
int board_pc_byte(uint8_t *byte) { uint32_t time; return pop(&pc,byte,&time); }
int board_pc_timed_byte(uint8_t *byte, uint32_t *time) { return pop(&pc,byte,time); }
void board_flush_pc(void)
{
    __disable_irq(); pc.tail=pc.head; __enable_irq();
}
void board_flush_vision(void)
{
    __disable_irq(); vision.tail=vision.head; __enable_irq();
}
int board_take_fault(void)
{
    int result;
    __disable_irq(); result=fault; fault=0;
    if (result) { vision.tail=vision.head; pc.tail=pc.head; }
    __enable_irq(); return result;
}
int board_button(void) { return (R(GPIOA+0x10)&1u)!=0; }
void board_outputs(int enabled, uint16_t pan, uint16_t tilt)
{
    /* Foreground only: keep the permit check and enable indivisible to SysTick. */
    __disable_irq();
    if (enabled && (pan<PAN_MIN_US || pan>PAN_MAX_US || tilt<TILT_MIN_US || tilt>TILT_MAX_US))
        guard_fail(BOARD_GUARD_RANGE);
    if (!guard_active || guard_event || fault || board_button() ||
        (uint32_t)(milliseconds-guard_received)>=SAFETY_LEASE_MS) enabled=0;
    if (!enabled) {
        force_off();
    } else {
        R(TIM4+0x34)=pan; R(TIM4+0x38)=tilt;
        if (!pwm_enabled) {
            R(TIM4+0x14)=1;
            pin(GPIOD,12,2,2); pin(GPIOD,13,2,2);
            R(TIM4+0x20)=(1u<<0)|(1u<<4); pwm_enabled=1;
        }
    }
    __enable_irq();
}
int board_guard_refresh(uint32_t received)
{
    int accepted=0;
    __disable_irq();
    if (!guard_event && !fault && !board_button() &&
        (uint32_t)(milliseconds-received)<SAFETY_LEASE_MS) {
        guard_received=received; guard_active=1; accepted=1;
    }
    __enable_irq(); return accepted;
}
void board_guard_disarm(void)
{
    __disable_irq(); guard_active=0; force_off(); __enable_irq();
}
unsigned board_guard_take_event(void)
{
    unsigned result;
    __disable_irq(); result=guard_event; guard_event=0; __enable_irq(); return result;
}
/* HSI remains SYSCLK at 16MHz. PLL is used only for PLL48/RNG, not PWM/UART.
 * No entropy fallback to a fixed ID, uptime, or previous session is permitted. */
int board_session_nonce(uint32_t *hi, uint32_t *lo)
{
    unsigned i, n; uint32_t value[2], status; volatile uint32_t dummy;
    *hi=*lo=0;
    if ((R(RCC+8)&12u)!=0) return 0;
    R(RCC)&=~(1u<<24);
    for(i=0;i<100000u && (R(RCC)&(1u<<25));++i) { }
    if(i==100000u) return 0;
    R(RCC+4)=16u|(192u<<6)|(4u<<24); /* M16 N192 P2 Q4, HSI -> 48MHz */
    R(RCC)|=1u<<24;
    for(i=0;i<100000u && !(R(RCC)&(1u<<25));++i) { }
    if(i==100000u) return 0;
    R(RCC+0x34)|=1u<<6; dummy=R(RCC+0x34); (void)dummy;
    R(RCC+0x14)|=1u<<6; R(RCC+0x14)&=~(1u<<6);
    R(0x50060800u)=4u;
    for(n=0;n<2;++n) {
        for(i=0;i<100000u;++i) {
            status=R(0x50060804u);
            if(status&0x66u) return 0;
            if(status&1u) break;
        }
        if(i==100000u) return 0;
        value[n]=R(0x50060808u);
        if(!value[n]) return 0;
    }
    if(value[0]==value[1]) return 0;
    *hi=value[0]; *lo=value[1]; return 1;
}
int board_send(const char *line)
{
    unsigned n=(unsigned)strlen(line), i;
    unsigned free=(tx_tail-tx_head-1u)&511u;
    if (n>free) return 0;
    for (i=0;i<n;++i) { tx[tx_head]=line[i]; tx_head=(tx_head+1)&511u; }
    return 1;
}
void board_poll_tx(void)
{
    if (tx_head!=tx_tail && (R(CONSOLE)&(1u<<7))) {
        R(CONSOLE+4)=(uint8_t)tx[tx_tail]; tx_tail=(tx_tail+1)&511u;
    }
}
