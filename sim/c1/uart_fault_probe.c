/* Host-only test wrapper: exercises the actual UART ISR and queue code. */
#include "team_adapter.c"
API void inject_uart(unsigned port, unsigned status, unsigned byte) {
    uint32_t uart = port == 2 ? U2 : U3;
    R(uart) = status; R(uart + 4) = byte;
    if (port == 2) USART2_IRQHandler(); else USART3_IRQHandler();
    R(uart) = 0;
}
API unsigned uart_fault_field(unsigned field) {
    board_uart_fault_t s;
    if (!board_uart_fault_snapshot(&s)) return 0xffffffffu;
    switch (field) {
    case 0: return s.port;
    case 1: return s.sr_errors;
    case 2: return s.queue_full;
    default: return s.time_ms;
    }
}
