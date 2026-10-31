#ifndef SKYSTAR_BOARD_H
#define SKYSTAR_BOARD_H
#include <stdint.h>
#ifndef CONSOLE_USART
#define CONSOLE_USART 1
#endif
#if CONSOLE_USART != 1 && CONSOLE_USART != 3
#error Unsupported CONSOLE_USART
#endif
#if CONSOLE_USART == 3
#define CONSOLE_LABEL "USART3_PC10_PC11"
#else
#define CONSOLE_LABEL "USART1_PA9_PA10"
#endif
void board_init(void);
uint32_t board_ms(void);
int board_vision_byte(uint8_t *byte, uint32_t *received);
int board_pc_byte(uint8_t *byte);
int board_pc_timed_byte(uint8_t *byte, uint32_t *received);
void board_flush_pc(void);
void board_flush_vision(void);
int board_take_fault(void);
int board_button(void);
void board_outputs(int enabled, uint16_t pan, uint16_t tilt);
int board_send(const char *line);
void board_poll_tx(void);
#define BOARD_GUARD_LEASE 1u
#define BOARD_GUARD_KEY 2u
#define BOARD_GUARD_UART 3u
#define BOARD_GUARD_RANGE 4u
int board_guard_refresh(uint32_t received);
void board_guard_disarm(void);
unsigned board_guard_take_event(void);
/* Bounded hardware RNG acquisition; failure must prohibit arming. */
int board_session_nonce(uint32_t *hi, uint32_t *lo);
#endif
