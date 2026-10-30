#ifndef SKYSTAR_BOARD_H
#define SKYSTAR_BOARD_H
#include <stdint.h>
void board_init(void);
uint32_t board_ms(void);
int board_vision_byte(uint8_t *byte, uint32_t *received);
int board_pc_byte(uint8_t *byte);
void board_flush_vision(void);
int board_take_fault(void);
int board_button(void);
void board_outputs(int enabled, uint16_t pan, uint16_t tilt);
int board_send(const char *line);
void board_poll_tx(void);
#endif
