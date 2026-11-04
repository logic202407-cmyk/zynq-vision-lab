/* Host-only test wrapper: exercises the actual UART ISR and queue code. */
#include "team_adapter.c"
API void inject_uart(unsigned port, unsigned status, unsigned byte) {
    uint32_t uart = port == 2 ? U2 : U3;
    R(uart) = status; R(uart + 4) = byte;
    if (port == 2) USART2_IRQHandler(); else USART3_IRQHandler();
    R(uart) = 0;
}
