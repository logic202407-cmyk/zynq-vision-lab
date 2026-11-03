/**
 * @file    servo.h
 * @brief   双轴舵机 PWM 驱动 — TIM2 50Hz, PA0/PA1
 * @note    定时器配置: PSC=71, ARR=19999 → 1us分辨率, 20ms周期
 *
 *          脉冲范围: 500us(0°) ~ 1500us(90°) ~ 2500us(180°)
 *          Pan 为 270° 数字舵机, 安全范围: 600us ~ 2400us
 *          Tilt 为 180° 数字舵机, 安全范围: 1000us ~ 2400us (已实测)
 *
 *          接线:
 *            PA0 = TIM2_CH1 = Pan  水平旋转舵机
 *            PA1 = TIM2_CH2 = Tilt 俯仰舵机
 *            舵机电源: 外部 5V (不可从 STM32 3.3V 取电)
 *            共地:   STM32 G — 舵机 GND — 外部电源 GND
 */

#ifndef __SERVO_H
#define __SERVO_H

#include "stm32f10x.h"

/* ===== 脉宽限值 ===== */
#define SERVO_PULSE_MIN    500    /* 0°   (实际可能机械限位到 1000) */
#define SERVO_PULSE_MAX    2500   /* 180° (实际可能机械限位到 2000) */
#define SERVO_PULSE_MID    1500   /* 90°  中点 */

#define PAN_HOME_US         1450   /* Pan 机械正前方对应脉宽, 按实际硬件调 */
#define PAN_SWEEP_OFFSET_US 800    /* 复位自检左右摆动的幅度 */

#define TILT_HOME_US        1500   /* Tilt 正前方/中位对应脉宽 */
#define TILT_SWEEP_OFFSET_US 400   /* 复位自检上下摆动的幅度 */

/* ===== 安全裁剪（PID 阶段用，按实际机械范围调整） ===== */
#define PAN_SERVO_MAX_ANGLE 270
#define PAN_SAFE_MIN        600    /* 约 13.5° */
#define PAN_SAFE_MAX        2400   /* 约 256.5° */
#define TILT_SAFE_MIN       1000   /* 约 45° */
#define TILT_SAFE_MAX       2400   /* 约 171° */

void servo_init(void);
void servo_set_pan_us(int32_t pulse_us);
void servo_set_tilt_us(int32_t pulse_us);
void servo_set_angle_pan(uint16_t angle_deg);   /* 0°~270° */
void servo_set_angle_tilt(uint16_t angle_deg);

#endif /* __SERVO_H */
