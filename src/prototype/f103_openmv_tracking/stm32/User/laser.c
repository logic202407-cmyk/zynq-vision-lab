#include "laser.h"
static volatile uint8_t s_on;

void laser_init(void)
{
    GPIO_InitTypeDef gpio;
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOB, ENABLE);
    GPIO_ResetBits(LASER_GPIO_PORT, LASER_GPIO_PIN);
    gpio.GPIO_Pin = LASER_GPIO_PIN;
    gpio.GPIO_Mode = GPIO_Mode_Out_PP;
    gpio.GPIO_Speed = GPIO_Speed_2MHz;
    GPIO_Init(LASER_GPIO_PORT, &gpio);
    s_on = 0;
}
void laser_off(void)
{
    GPIO_ResetBits(LASER_GPIO_PORT, LASER_GPIO_PIN);
    s_on = 0;
}
void laser_set(uint8_t enabled)
{
    if (enabled) {
        GPIO_SetBits(LASER_GPIO_PORT, LASER_GPIO_PIN);
        s_on = 1;
    } else laser_off();
}
uint8_t laser_is_on(void) { return s_on; }
