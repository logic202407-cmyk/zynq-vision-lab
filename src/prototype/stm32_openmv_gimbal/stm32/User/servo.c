#include "stm32f10x.h"
#include "servo.h"
static uint16_t clamp(int32_t value, uint16_t lo, uint16_t hi)
{
    return value < lo ? lo : value > hi ? hi : (uint16_t)value;
}
void servo_init(void)
{
    GPIO_InitTypeDef gpio;
    TIM_TimeBaseInitTypeDef timer;
    TIM_OCInitTypeDef output;
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA, ENABLE);
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_TIM2, ENABLE);
    gpio.GPIO_Pin = GPIO_Pin_0 | GPIO_Pin_1;
    gpio.GPIO_Mode = GPIO_Mode_AF_PP;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOA, &gpio);
    TIM_TimeBaseStructInit(&timer);
    timer.TIM_Prescaler = 71;
    timer.TIM_Period = 19999;
    TIM_TimeBaseInit(TIM2, &timer);
    TIM_OCStructInit(&output);
    output.TIM_OCMode = TIM_OCMode_PWM1;
    output.TIM_OutputState = TIM_OutputState_Enable;
    output.TIM_OCPolarity = TIM_OCPolarity_High;
    output.TIM_Pulse = PAN_HOME_US;
    TIM_OC1Init(TIM2, &output);
    output.TIM_Pulse = TILT_HOME_US;
    TIM_OC2Init(TIM2, &output);
    TIM_OC1PreloadConfig(TIM2, TIM_OCPreload_Enable);
    TIM_OC2PreloadConfig(TIM2, TIM_OCPreload_Enable);
    TIM_ARRPreloadConfig(TIM2, ENABLE);
    TIM_Cmd(TIM2, ENABLE);
}
void servo_set_pan_us(int32_t v) { TIM_SetCompare1(TIM2, clamp(v, PAN_SAFE_MIN, PAN_SAFE_MAX)); }
void servo_set_tilt_us(int32_t v) { TIM_SetCompare2(TIM2, clamp(v, TILT_SAFE_MIN, TILT_SAFE_MAX)); }
