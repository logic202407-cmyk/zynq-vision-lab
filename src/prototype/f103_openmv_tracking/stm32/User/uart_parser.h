/**
 * @file    uart_parser.h
 * @brief   串口解析状态机 — 解析 OpenMV 8字节定长帧
 *
 * 帧格式 (8字节):
 *   [0] 0xAA   帧头1
 *   [1] 0xFF   帧头2
 *   [2] dx_lo  (int16 小端序)
 *   [3] dx_hi
 *   [4] dy_lo  (int16 小端序)
 *   [5] dy_hi
 *   [6] flag   0x01=识别到目标  0x00=丢失
 *   [7] 0xEE   帧尾
 */

#ifndef __UART_PARSER_H
#define __UART_PARSER_H

#include <stdint.h>

/* ===== 状态机状态 ===== */
typedef enum {
    STATE_SYNC_H1 = 0,   /* 等待帧头 0xAA */
    STATE_SYNC_H2,       /* 等待帧头 0xFF */
    STATE_RECV_PAYLOAD   /* 接收 6 字节载荷；完成后继续接收下一帧 */
} parser_state_t;

/* ===== 解析结果 ===== */
typedef struct {
    int16_t dx;       /* X 轴偏差 (像素) */
    int16_t dy;       /* Y 轴偏差 (像素) */
    uint8_t flag;     /* 0x01=锁定, 0x00=丢失 */
} track_target_t;

/* ===== 解析器句柄 ===== */
typedef struct {
    parser_state_t   state;         /* 当前状态 */
    uint8_t          buf[6];        /* 载荷缓冲区 */
    uint8_t          idx;           /* 缓冲区写入位置 */
    track_target_t   target;        /* 解析完成的目标数据 */
    volatile uint8_t frame_ready;   /* 非 0 = 有新帧待消费 (中断写/主循环读清) */
    uint32_t         total_frames;  /* 累计正确帧数 (调试用) */
    uint32_t         err_tail;      /* 帧尾错误计数 (调试用) */
    volatile uint32_t faults;       /* 畸形帧/串口错误/半帧超时 */
    uint32_t         last_byte_ms;
    uint32_t         received_ms;
} uart_parser_t;

/* ===== API ===== */
void    uart_parser_init(uart_parser_t *p);
void    uart_parser_feed(uart_parser_t *p, uint8_t byte, uint32_t now_ms);
uint8_t uart_parser_consume(uart_parser_t *p, track_target_t *out);
void    uart_parser_fault(uart_parser_t *p);
void    uart_parser_expire(uart_parser_t *p, uint32_t now_ms);

#endif /* __UART_PARSER_H */
