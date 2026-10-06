/* Stub only MCU register I/O; compile the real status driver and application C. */
#include "stm32f10x.h"
#include "usart3_config.h"
#include "usart_config.h"
#include <string.h>
#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT __attribute__((visibility("default")))
#endif
static control_t controller;
static uart_parser_t parser;
static char captured[2048];
static unsigned used, ready, flag_checks, pins, uart_mode, rx_interrupts;
uint32_t SystemCoreClock = 72000000u;
unsigned SysTick_Config(uint32_t ticks) { (void)ticks; return 0; }
void serial_rx_init(unsigned port) { (void)port; }
void serial_rx_interrupt(unsigned port) { (void)port; }
int serial_rx_pop(unsigned port, rx_byte_t *out) { (void)port; (void)out; return 0; }
void usart1_init(void) { }
unsigned USART_GetFlagStatus(unsigned uart, unsigned flag)
{
    (void)uart; (void)flag;
    ++flag_checks;
    /* Bound accidental busy loops; the test still detects repeated flag reads. */
    return ready || flag_checks > 3u ? SET : RESET;
}
void USART_SendData(unsigned uart, uint16_t value)
{
    (void)uart;
    if (used + 1u < sizeof(captured)) {
        captured[used++] = (char)value;
        captured[used] = 0;
    }
}
void RCC_APB2PeriphClockCmd(unsigned clocks, unsigned enable) { (void)clocks; (void)enable; }
void RCC_APB1PeriphClockCmd(unsigned clocks, unsigned enable) { (void)clocks; (void)enable; }
void GPIO_Init(unsigned gpio, const GPIO_InitTypeDef *config) { (void)gpio; pins |= config->GPIO_Pin; }
void USART_StructInit(USART_InitTypeDef *config) { config->USART_BaudRate = 9600; config->USART_Mode = 12; }
void USART_Init(unsigned uart, const USART_InitTypeDef *config) { (void)uart; uart_mode = config->USART_Mode; }
void NVIC_Init(const NVIC_InitTypeDef *config) { (void)config; }
void USART_ITConfig(unsigned uart, unsigned interrupt, unsigned enable)
{ (void)uart; (void)interrupt; rx_interrupts += enable; }
void USART_Cmd(unsigned uart, unsigned enable) { (void)uart; (void)enable; }
EXPORT void log_reset(void)
{
    used = flag_checks = pins = rx_interrupts = 0;
    captured[0] = 0; ready = 1;
    control_init(&controller); uart_parser_init(&parser); usart3_init();
}
EXPORT void log_ready(unsigned value) { ready = value; flag_checks = 0; }
EXPORT void log_clear(void) { used = 0; captured[0] = 0; }
EXPORT void log_queue(unsigned frame)
{
    controller.session = 7;
    controller.frame = frame;
    usart3_send_status(&controller, &parser);
}
EXPORT void log_maximum(void)
{
    controller.session = controller.frame = controller.received_ms = controller.source_ms = UINT32_MAX;
    controller.rejected = parser.rejected = UINT32_MAX;
    controller.state = OBS_NO_TARGET;
    controller.last_reject = parser.last_reject = REJECT_OVERFLOW;
    controller.dx = -80; controller.dy = -60;
    controller.pan_us = controller.tilt_us = 2400;
    controller.requested_pan = controller.requested_tilt = 2400;
    controller.pan_pid.Kp = controller.pan_pid.Ki = controller.pan_pid.Kd = 50;
    controller.tilt_pid.Kp = controller.tilt_pid.Ki = controller.tilt_pid.Kd = 50;
    usart3_send_status(&controller, &parser);
}
EXPORT void log_poll(void) { usart3_poll_tx(); }
EXPORT const char *log_text(void) { return captured; }
EXPORT unsigned log_checks(void) { return flag_checks; }
EXPORT unsigned log_pins(void) { return pins; }
EXPORT unsigned log_mode(void) { return uart_mode; }
EXPORT unsigned log_rx_interrupts(void) { return rx_interrupts; }
