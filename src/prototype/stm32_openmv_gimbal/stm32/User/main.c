/* Independent stm32-p0/v1 firmware. Compile-only until a separate bench test. */
#include "stm32f10x.h"
#include "control.h"
#include "command.h"
#include "uart_parser.h"
#ifndef P0_LOG_ONLY
#include "servo.h"
#endif
#include "usart_config.h"
#include "usart3_config.h"
volatile uint32_t g_ms_tick = 0;
static control_t controller;
static uart_parser_t parser;
static command_t console;
#ifndef P0_LOG_ONLY
static void apply_output(void)
{
    if (controller.updated) {
        servo_set_pan_us(controller.pan_us);
        servo_set_tilt_us(controller.tilt_us);
    }
}
#else
#define apply_output() ((void)0)
#endif
int main(void)
{
    uint32_t status_ms = 0;
    control_init(&controller);
    uart_parser_init(&parser);
    command_init(&console);
#ifndef P0_LOG_ONLY
    servo_init();
#endif
    (void)SysTick_Config(SystemCoreClock / 1000);
    usart1_init();
    usart3_init();
    for (;;) {
        rx_byte_t byte;
        int result, status_requested = 0;
        control_tick(&controller, g_ms_tick);
        while ((result = serial_rx_pop(3, &byte)) != 0) {
            if (result < 0) {
                console.used = console.overflow = 0;
                ++console.rejected;
                control_invalidate(&controller, REJECT_OVERFLOW);
                status_requested = 1;
            } else {
                result = command_feed(&console, &controller, byte.byte);
                if (result) { status_requested = 1; apply_output(); }
            }
        }
        while ((result = serial_rx_pop(1, &byte)) != 0) {
            if (result < 0) {
                parser.used = 0;
                ++parser.rejected;
                parser.last_reject = REJECT_OVERFLOW;
                control_invalidate(&controller, REJECT_OVERFLOW);
            } else {
                track_target_t target;
                uint32_t old_rejected = parser.rejected;
                int ready = uart_parser_feed(&parser, byte.byte, byte.received_ms, &target);
                if (parser.rejected != old_rejected)
                    control_invalidate(&controller, parser.last_reject);
                if (ready) { (void)control_frame(&controller, &target, g_ms_tick); apply_output(); }
            }
        }
        if (uart_parser_expire(&parser, g_ms_tick))
            control_invalidate(&controller, parser.last_reject);
        if (status_requested || (uint32_t)(g_ms_tick - status_ms) >= 50u) {
            status_ms = g_ms_tick;
            usart3_send_status(&controller, &parser);
        }
        usart3_poll_tx();
    }
}
