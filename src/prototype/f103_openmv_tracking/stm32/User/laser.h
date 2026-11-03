#ifndef LASER_H
#define LASER_H
#include "stm32f10x.h"

/* Confirmed wiring: PB0 -> MOS TRIG, active high. */
#define LASER_GPIO_PORT GPIOB
#define LASER_GPIO_PIN GPIO_Pin_0

void laser_init(void);
void laser_off(void);
void laser_set(uint8_t enabled);
uint8_t laser_is_on(void);
#endif
