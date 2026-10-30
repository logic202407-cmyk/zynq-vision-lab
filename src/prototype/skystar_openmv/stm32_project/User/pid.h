/**
 * @file    pid.h
 * @brief   位置式 PID 控制器 — 二维云台目标追踪
 *
 * 用法:
 *   pid_t pid;
 *   pid_init(&pid, 2.0f, 0.05f, 1.0f, -500.0f, 500.0f);
 *   // dt = 距上次调用的时间间隔(秒), 由 g_ms_tick 算出
 *   float correction = pid_update(&pid, 0.0f, measurement, dt);
 *   // correction 单位与 out_min/out_max 一致 (此处为 us)
 *
 * 注意: dt 参与积分与微分运算, 不能省略。
 *       传 0 或异常大的值会被内部兜底成 10ms。
 */

#ifndef __PID_H
#define __PID_H

typedef struct {
    float Kp;           /* 比例增益 */
    float Ki;           /* 积分增益 */
    float Kd;           /* 微分增益 */
    float integral;     /* 积分累加器 (单位: us, 已含 Ki 与 dt) */
    float integral_max; /* 预留 (当前实现用反算法抗饱和, 未使用) */
    float prev_error;   /* 上一次误差 (微分用) */
    float out_min;      /* 输出下限 (含抗积分饱和) */
    float out_max;      /* 输出上限 (含抗积分饱和) */
} pid_t;

void  pid_init(pid_t *pid, float Kp, float Ki, float Kd,
               float out_min, float out_max);
float pid_update(pid_t *pid, float setpoint, float measurement, float dt);
void  pid_reset(pid_t *pid);

#endif /* __PID_H */
