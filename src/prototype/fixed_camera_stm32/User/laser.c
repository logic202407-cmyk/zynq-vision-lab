/**
 * @file    laser.c
 * @brief   激光笔开关控制实现 — PA4 推挽输出驱动 N-MOS 模块
 * @note    接线、硬件前提与"为什么不用 PA0"见 laser.h;
 *          设计取舍与实测过程见 "实现说明_激光控制模块.md"
 */

#include "laser.h"

/* 软件记录的状态: 只反映"最后一次下发的电平", 不读回引脚。
 * 有它才能做到重复调用不重复写寄存器, 也让 laser_is_on() 可供上位机查询。 */
static uint8_t s_laser_on = 0;

/**
 * @brief  激光控制引脚初始化 — 上电默认关断
 * @note   顺序很关键: 先写输出锁存器(ODR)为 0, 再把引脚配成推挽输出。
 *         因为输入模式下 ODR 仍然可写且会被锁存, 切到输出模式的瞬间引脚
 *         就按 ODR=0 输出低电平。若反过来先配输出再写 0, 中间会有一小段
 *         时间输出的是复位值, 栅极上可能出现一个足以让 MOS 误导通的窄脉冲。
 */
void laser_init(void)
{
    GPIO_InitTypeDef gpio;

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA, ENABLE);

    /* 1) 先锁存 0 电平 (此时还是复位后的浮空输入, 不会真的输出) */
    GPIO_ResetBits(LASER_GPIO_PORT, LASER_GPIO_PIN);

    /* 2) 再切成推挽输出 */
    gpio.GPIO_Pin   = LASER_GPIO_PIN;
    gpio.GPIO_Mode  = GPIO_Mode_Out_PP;
    /* 开关信号没有速度要求, 2MHz 档边沿最缓, 对模拟部分和舵机干扰最小 */
    gpio.GPIO_Speed = GPIO_Speed_2MHz;
    GPIO_Init(LASER_GPIO_PORT, &gpio);

    /* 3) 双保险再写一次低电平 */
    GPIO_ResetBits(LASER_GPIO_PORT, LASER_GPIO_PIN);

    s_laser_on = 0;
}

void laser_on(void)
{
    if (s_laser_on) return;
    GPIO_SetBits(LASER_GPIO_PORT, LASER_GPIO_PIN);
    s_laser_on = 1;
}

void laser_off(void)
{
    if (!s_laser_on) return;
    GPIO_ResetBits(LASER_GPIO_PORT, LASER_GPIO_PIN);
    s_laser_on = 0;
}

void laser_set(uint8_t on)
{
    if (on) {
        laser_on();
    } else {
        laser_off();
    }
}

uint8_t laser_is_on(void)
{
    return s_laser_on;
}
