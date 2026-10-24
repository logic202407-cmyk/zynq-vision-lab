/**
 * @file    servo.c
 * @brief   双轴舵机 PWM 驱动实现 — TIM2 CH1(PA0) + CH2(PA1)
 */

#include "servo.h"

/* ===== 定时器参数 ===== */
#define TIM2_PSC         71        /* 72MHz / (71+1) = 1MHz, 1us/tick */
#define TIM2_ARR         19999     /* 20000-1, 20ms 周期 = 50Hz        */

/**
 * @brief  裁剪脉宽到安全范围
 */
static uint16_t clamp_pulse(int32_t us, uint16_t min_us, uint16_t max_us)
{
    if (us < (int32_t)min_us) return min_us;
    if (us > (int32_t)max_us) return max_us;
    return (uint16_t)us;
}

/**
 * @brief  舵机初始化: TIM2 CH1(PA0) + CH2(PA1), 50Hz PWM
 * @note   上电后舵机自动回中 (1500us)
 */
void servo_init(void)
{
    GPIO_InitTypeDef  gpio;
    TIM_TimeBaseInitTypeDef  tim_base;
    TIM_OCInitTypeDef tim_oc;

    /* 时钟: GPIOA + AFIO + TIM2 */
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA
                         | RCC_APB2Periph_AFIO, ENABLE);
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_TIM2, ENABLE);

    /* PA0 = TIM2_CH1, PA1 = TIM2_CH2 (复用推挽) */
    gpio.GPIO_Pin   = GPIO_Pin_0 | GPIO_Pin_1;
    gpio.GPIO_Mode  = GPIO_Mode_AF_PP;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOA, &gpio);

    /* TIM2 时基: 50Hz */
    TIM_TimeBaseStructInit(&tim_base);
    tim_base.TIM_Prescaler         = TIM2_PSC;
    tim_base.TIM_Period            = TIM2_ARR;
    tim_base.TIM_CounterMode       = TIM_CounterMode_Up;
    tim_base.TIM_ClockDivision     = TIM_CKD_DIV1;
    TIM_TimeBaseInit(TIM2, &tim_base);

    /* CH1 (PA0): PWM 模式 1 */
    TIM_OCStructInit(&tim_oc);
    tim_oc.TIM_OCMode      = TIM_OCMode_PWM1;
    tim_oc.TIM_OutputState = TIM_OutputState_Enable;
    tim_oc.TIM_OCPolarity  = TIM_OCPolarity_High;
    tim_oc.TIM_Pulse       = SERVO_PULSE_MID;  /* 初始居中 */
    TIM_OC1Init(TIM2, &tim_oc);

    /* CH2 (PA1): PWM 模式 1 */
    tim_oc.TIM_Pulse       = SERVO_PULSE_MID;
    TIM_OC2Init(TIM2, &tim_oc);

    /* CH1/CH2 预装载使能 */
    TIM_OC1PreloadConfig(TIM2, TIM_OCPreload_Enable);
    TIM_OC2PreloadConfig(TIM2, TIM_OCPreload_Enable);

    /* 自动重装载预装载 */
    TIM_ARRPreloadConfig(TIM2, ENABLE);

    /* 启动 TIM2 */
    TIM_Cmd(TIM2, ENABLE);
}

/* ===== 脉宽 API（PID 阶段主用） ===== */

void servo_set_pan_us(int32_t pulse_us)
{
    TIM_SetCompare1(TIM2, clamp_pulse(pulse_us, PAN_SAFE_MIN, PAN_SAFE_MAX));
}

void servo_set_tilt_us(int32_t pulse_us)
{
    TIM_SetCompare2(TIM2, clamp_pulse(pulse_us, TILT_SAFE_MIN, TILT_SAFE_MAX));
}

/* ===== 角度 API（测试 / 手动控制用） ===== */
/* Pan 270°: pulse = 500 + angle * (2000/270) ≈ 500 + angle * 7.41  */
/* Tilt 180°: pulse = 500 + angle * (2000/180) ≈ 500 + angle * 11.11 */

void servo_set_angle_pan(uint16_t angle_deg)
{
    uint32_t pulse;
    if (angle_deg > PAN_SERVO_MAX_ANGLE) angle_deg = PAN_SERVO_MAX_ANGLE;
    pulse = SERVO_PULSE_MIN + (uint32_t)angle_deg * 2000 / PAN_SERVO_MAX_ANGLE;
    servo_set_pan_us((uint16_t)pulse);
}

void servo_set_angle_tilt(uint16_t angle_deg)
{
    uint32_t pulse;
    if (angle_deg > 180) angle_deg = 180;
    pulse = SERVO_PULSE_MIN + (uint32_t)angle_deg * 2000 / 180;
    servo_set_tilt_us((uint16_t)pulse);
}
