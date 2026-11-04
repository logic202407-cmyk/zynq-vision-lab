/**
 * @file    pid.c
 * @brief   位置式 PID 实现 — 输出绝对值 (非增量)
 */

#include "pid.h"

/**
 * @brief  初始化 PID 控制器
 * @param out_min / out_max  输出限幅 (us)
 * @note   不再用"把累加器卡在某个上限"的方式抗饱和 (那种做法限的是像素累加值,
 *         量纲和输出 us 对不上, 等于没限)。现在由 pid_update 做反算抗饱和,
 *         所以 integral_max 只是为兼容保留, 全程不使用。
 *         若整定过程中 Ki 被在线改成 0, 积分项会自动清零停用 (见 pid_update)。
 */
void pid_init(pid_t *pid, float Kp, float Ki, float Kd,
              float out_min, float out_max)
{
    pid->Kp           = Kp;
    pid->Ki           = Ki;
    pid->Kd           = Kd;
    pid->integral     = 0.0f;
    pid->integral_max = 0.0f;
    pid->prev_error   = 0.0f;
    pid->out_min      = out_min;
    pid->out_max      = out_max;
}

/**
 * @brief  执行一次 PID 计算 (带时间基准)
 * @param  setpoint     期望值 (目标在画面中心 = 0)
 * @param  measurement  当前测量值 (dx 或 dy, 像素)
 * @param  dt           距上次调用的时间间隔 (秒), 必须 > 0
 * @return 控制量 (脉宽修正值, us), 已限幅到 [out_min, out_max]
 *
 * 为什么必须传 dt:
 *   积分项是 "误差对时间的积分", 微分项是 "误差对时间的导数"。
 *   早期版本写成 integral += error, D = Kd*(error-prev_error), 都省掉了 dt,
 *   后果是 Kp/Ki/Kd 的实际效果随调用频率漂移 —— OpenMV 帧率一变
 *   (目标大小/光照都会影响), 同一组参数的表现就完全不同, 调参结果无法复现。
 *   更严重的是积分累加没有 dt 时量纲是"像素·帧数", 帧率越高累积越快,
 *   只要 Ki 稍大就立刻饱和, 于是 Ki 根本没法用。
 *
 * 抗积分饱和用"反算+钳位"而不是简单卡累加器:
 *   先让积分项单独受输出限幅约束, 若积分项已被钳在限幅上且误差还在把它
 *   往同方向推, 就不再累加。这样 Ki 在线改变时不需要重算任何上限。
 */
float pid_update(pid_t *pid, float setpoint, float measurement, float dt)
{
    float error = setpoint - measurement;   /* error = -measurement (中心=0) */
    float P, I, D, output;

    /* 防御: dt 非法时退回 10ms, 避免除零或积分爆炸 */
    if (dt <= 0.0f || dt > 1.0f) {
        dt = 0.01f;
    }

    /* ---- 比例项 ---- */
    P = pid->Kp * error;

    /* ---- 积分项 ---- */
    if (pid->Ki > 0.0f) {
        /* 积分变化量 = Ki * error * dt (单位: us) */
        float delta = pid->Ki * error * dt;

        /* 反算抗饱和: 只有在没有把积分往饱和方向推的时候才累加 */
        if (!((pid->integral >= pid->out_max && delta > 0.0f) ||
              (pid->integral <= pid->out_min && delta < 0.0f))) {
            pid->integral += delta;
        }

        /* 积分项自身也不得超出输出范围 */
        if      (pid->integral > pid->out_max) pid->integral = pid->out_max;
        else if (pid->integral < pid->out_min) pid->integral = pid->out_min;

        I = pid->integral;
    } else {
        /* Ki == 0: 清掉历史积分, 避免以后把 Ki 调上来时旧值突然生效 */
        pid->integral = 0.0f;
        I = 0.0f;
    }

    /* ---- 微分项: 对误差求时间导数 ---- */
    D = pid->Kd * (error - pid->prev_error) / dt;
    pid->prev_error = error;

    /* ---- 合成 + 输出限幅 ---- */
    output = P + I + D;
    if      (output > pid->out_max) output = pid->out_max;
    else if (output < pid->out_min) output = pid->out_min;

    return output;
}

/**
 * @brief  复位 PID 状态 (丢目标时调用, 防止积分残留)
 */
void pid_reset(pid_t *pid)
{
    pid->integral   = 0.0f;
    pid->prev_error = 0.0f;
}
