/**
 * @file    laser.h
 * @brief   激光笔开关控制 — N-MOS 开关模块驱动, 控制引脚 PA4
 * @note    STM32F103C8T6 + 标准外设库 V3.5.0
 *          设计与实测过程见仓库根目录 "实现说明_激光控制模块.md"
 *
 * ===== 接线 =====
 *   MOS VIN+ -> 外部 5V 电源正极        MOS VOUT+ -> 激光笔红线
 *   MOS VIN- -> 电源 GND (与 STM32 共地) MOS VOUT- -> 激光笔黑线
 *   MOS TRIG -> STM32 PA4               MOS GND   -> STM32 GND
 *   TRIG 与 GND 之间并 10k 下拉电阻 (必须, 原因见下)
 *
 * 控制逻辑: PA4 = 1 (3.3V) -> MOS 导通 -> 激光亮
 *           PA4 = 0 (0V)   -> MOS 截止 -> 激光灭
 * STM32 只输出控制信号, 不为激光笔提供工作电流。
 *
 * ===== 两条硬件前提 =====
 *   1) 栅极 10k 下拉电阻: STM32 复位期间引脚是高阻浮空, 没有这颗电阻时栅极
 *      可能被漏电/干扰抬起来, MOS 误导通 —— 上电瞬间激光就亮, 而这段时间
 *      软件管不到。本机已焊。
 *   2) MOS 要用 3.3V 能完全导通的逻辑电平管 (AO3400 / SI2302 / IRLZ44N 等)。
 *      IRF520 这类 Vgs(th) 2~4V 的管子用 3.3V 只能半导通: 激光偏暗、MOS 发热。
 *
 * ===== 为什么是 PA4, 不是 PA0 =====
 *   PA0 在本工程里是 TIM2_CH1 的 Pan 舵机 PWM 输出 (见 servo.h)。
 *   舵机 50Hz 方波会把激光斩波、栅极电容会拖累舵机信号, 推挽输出还会与
 *   定时器复用推挽互相覆盖。PA4 完全空闲、无复用、无需重映射。
 *
 * ===== 上电默认关断 =====
 *   laser_init() 先把输出锁存器(ODR)写 0, 再切成推挽输出, 切换瞬间就是低电平。
 *   复位到 laser_init() 之间的空档由上面那颗 10k 下拉电阻兜住, 两层合起来
 *   才能保证"上电不出光"。
 */

#ifndef __LASER_H
#define __LASER_H

#include "stm32f10x.h"

/* ===== 控制引脚 ===== */
#define LASER_GPIO_PORT   GPIOA
#define LASER_GPIO_PIN    GPIO_Pin_4      /* PA4 */

/* ===== API ===== */
void    laser_init(void);       /* 初始化引脚, 并保证输出为低(激光灭) */
void    laser_on(void);         /* 开激光 (重复调用不会重复写寄存器) */
void    laser_off(void);        /* 关激光 */
void    laser_set(uint8_t on);  /* 按判定结果开关, 联调阶段主用 */
uint8_t laser_is_on(void);      /* 软件记录的当前状态: 1=开 0=关 */

#endif /* __LASER_H */
