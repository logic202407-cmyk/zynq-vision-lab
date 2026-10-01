/**
 * @file    usart3_config.h
 * @brief   USART3 调参串口 — PB10(TX)/PB11(RX), 接 USB-TTL 到电脑
 */

#ifndef __USART3_CONFIG_H
#define __USART3_CONFIG_H

#include "stm32f10x.h"
#include "pid.h"

void usart3_init(pid_t *pan_pid, pid_t *tilt_pid);
uint8_t usart3_status_requested(void);

void usart3_send_status(int16_t dx, int16_t dy,
                        uint16_t pan_us, uint16_t tilt_us,
                        const pid_t *pan_pid, const pid_t *tilt_pid);

/* ===== 手动控制 (调试用, 脱离摄像头直接驱动舵机) =====
 * 命令 (换行结尾):
 *     pan 1500      直接给 Pan 舵机 1500us, 并进入手动模式
 *     tlt 1200      直接给 Tilt 舵机 1200us, 并进入手动模式
 *     auto          退出手动模式, 回到 OpenMV 追踪
 * 手动模式下 main 循环不跑 PID, 舵机停在指定脉宽。
 * 脉宽会被裁剪到机械安全范围, 传错值不会打坏舵机。 */
uint8_t  usart3_manual_active(void);
uint16_t usart3_manual_pan_us(void);
uint16_t usart3_manual_tilt_us(void);
/* 手动命令序号: 每收到一条 pan/tlt/auto 就 +1。
 * main 循环比对序号变化来决定是否重新下发脉宽 —— 这样连续发多条
 * pan 命令都能逐条生效 (否则只能生效第一条)。 */
uint8_t  usart3_manual_seq(void);

#endif /* __USART3_CONFIG_H */
