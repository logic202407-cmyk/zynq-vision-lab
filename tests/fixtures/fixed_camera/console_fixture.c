/* Execute the unchanged device console loop against a deterministic fake UART.
 * This tests application behavior, not real electrical UART or PWM timing. */
#include <setjmp.h>
#include <string.h>
#include "circle_draw.h"
static void fixture_tick(circle_draw_t *value, uint32_t now);
#define circle_tick fixture_tick
#include "circle_console.c"
#undef circle_tick

USART_TypeDef fixture_uart;
uint32_t SystemCoreClock = 72000000U;
volatile uint32_t g_ms_tick;
typedef struct {
    uint32_t at, flags;
    unsigned length, index;
    unsigned char bytes[256];
} fixture_event;
static fixture_event events[32];
static unsigned event_count, event_index, tx_length, servo_starts;
static char tx[16384];
static unsigned laser_level, pulse_count, off_count;
static uint32_t on_times[16], off_times[16], end_ms;
static uint16_t pan_out, tilt_out;
static jmp_buf finished;

static void step(void)
{
    fixture_event *event;
    if (g_ms_tick >= end_ms) longjmp(finished, 1);
    g_ms_tick++;
    fixture_uart.SR = USART_FLAG_TXE;
    if (event_index >= event_count) return;
    event = &events[event_index];
    if (g_ms_tick < event->at) return;
    fixture_uart.DR = event->bytes[event->index++];
    fixture_uart.SR |= USART_FLAG_RXNE | event->flags;
    event->flags = 0;
    if (event->index == event->length) event_index++;
}

/* Advance once per console loop, including loops with extra off() calls. */
static void fixture_tick(circle_draw_t *value, uint32_t now)
{
    circle_tick(value, now);
    step();
}

int USART_GetFlagStatus(USART_TypeDef *port, uint16_t flag)
{ (void)port; (void)flag; return 1; }
void USART_SendData(USART_TypeDef *port, uint16_t byte)
{
    (void)port;
    if (tx_length + 1U < sizeof(tx)) {
        tx[tx_length++] = (char)byte;
        tx[tx_length] = '\0';
    }
}
uint16_t USART_ReceiveData(USART_TypeDef *port)
{ port->SR &= ~USART_FLAG_RXNE; return (uint16_t)port->DR; }
void servo_init(void) { servo_starts++; pan_out = tilt_out = 1500; }
void servo_set_pan_us(int32_t value) { pan_out = (uint16_t)value; }
void servo_set_tilt_us(int32_t value) { tilt_out = (uint16_t)value; }
void laser_on(void)
{
    if (!laser_level && pulse_count < 16U) on_times[pulse_count++] = g_ms_tick;
    laser_level = 1;
}
void laser_off(void)
{
    if (laser_level && off_count < 16U) off_times[off_count++] = g_ms_tick;
    laser_level = 0;
}

void fixture_reset(void)
{
    memset(events, 0, sizeof(events));
    memset(tx, 0, sizeof(tx));
    memset(&draw, 0, sizeof(draw));
    memset(on_times, 0, sizeof(on_times));
    memset(off_times, 0, sizeof(off_times));
    event_count = event_index = tx_length = servo_starts = 0;
    laser_level = pulse_count = off_count = 0;
    motors_ready = size_set = 0;
    g_ms_tick = 0; pan_out = tilt_out = 0;
    fixture_uart.SR = USART_FLAG_TXE;
    fixture_uart.DR = 0;
}
int fixture_schedule(uint32_t at, const unsigned char *bytes, unsigned length, uint32_t flags)
{
    fixture_event *event;
    if (event_count >= 32U || !length || length > 256U
        || (event_count && at < events[event_count - 1U].at)) return 0;
    event = &events[event_count++];
    event->at = at; event->length = length; event->flags = flags;
    memcpy(event->bytes, bytes, length);
    return 1;
}
void fixture_run(uint32_t until)
{
    end_ms = until;
    if (setjmp(finished) == 0) circle_console_run();
}
const char *fixture_output(void) { return tx; }
unsigned fixture_servo_starts(void) { return servo_starts; }
unsigned fixture_pulses(void) { return pulse_count; }
unsigned fixture_laser(void) { return laser_level; }
unsigned fixture_pan(void) { return pan_out; }
unsigned fixture_tilt(void) { return tilt_out; }
unsigned fixture_state(void) { return (unsigned)draw.state; }
unsigned fixture_fault(void) { return draw.timing_fault; }
uint32_t fixture_on(unsigned index) { return index < pulse_count ? on_times[index] : 0; }
uint32_t fixture_off(unsigned index) { return index < off_count ? off_times[index] : 0; }
