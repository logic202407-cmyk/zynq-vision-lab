/**
 * @file    uart_parser.c
 * @brief   串口解析状态机实现 — 在 USART RX 中断中逐字节调用
 */

#include "uart_parser.h"

#define HEADER1       0xAA
#define HEADER2       0xFF
#define TAIL          0xEE
#define PAYLOAD_SIZE  6
#define IDX_TAIL      5

void uart_parser_init(uart_parser_t *p)
{
    p->state        = STATE_SYNC_H1;
    p->idx          = 0;
    p->frame_ready  = 0;
    p->total_frames = 0;
    p->err_tail     = 0;
    p->faults       = 0;
    p->last_byte_ms = p->received_ms = 0;
    p->target.dx    = 0;
    p->target.dy    = 0;
    p->target.flag  = 0;
}

/**
 * @brief  喂入一个字节 — 在 USART1_IRQHandler 中调用
 *
 * 状态转移:
 *   SYNC_H1 ──0xAA──▶ SYNC_H2
 *   SYNC_H1 ──else──▶ 停留 (丢弃)
 *
 *   SYNC_H2 ──0xFF──▶ RECV_PAYLOAD, idx=0
 *   SYNC_H2 ──0xAA──▶ 停留 (刷新起始点)
 *   SYNC_H2 ──else──▶ SYNC_H1
 *
 *   RECV_PAYLOAD ──存 buf[idx++], idx<6──▶ 停留
 *   RECV_PAYLOAD ──idx==6 且 tail==0xEE──▶ SYNC_H1 (校验并更新结果邮箱)
 *   RECV_PAYLOAD ──idx==6 且 tail!=0xEE──▶ SYNC_H1 (帧废弃)
 *
 *   主循环在短临界区消费邮箱，接收不中断；未消费覆盖会增加 faults。
 */
void uart_parser_fault(uart_parser_t *p)
{
    p->faults++;
    p->state = STATE_SYNC_H1;
    p->idx = p->frame_ready = 0;
    p->target.flag = 0;
}

void uart_parser_expire(uart_parser_t *p, uint32_t now_ms)
{
    if ((p->state == STATE_SYNC_H2 || p->state == STATE_RECV_PAYLOAD) &&
        (uint32_t)(now_ms - p->last_byte_ms) >= 20u)
        uart_parser_fault(p);
}

void uart_parser_feed(uart_parser_t *p, uint8_t byte, uint32_t now_ms)
{
    uart_parser_expire(p, now_ms);
    p->last_byte_ms = now_ms;
    switch (p->state) {

    case STATE_SYNC_H1:
        if (byte == HEADER1) {
            p->state = STATE_SYNC_H2;
        }
        break;

    case STATE_SYNC_H2:
        if (byte == HEADER2) {
            p->state = STATE_RECV_PAYLOAD;
            p->idx   = 0;
        } else if (byte == HEADER1) {
            /* 重复 0xAA, 保持当前状态 */
        } else {
            p->state = STATE_SYNC_H1;
        }
        break;

    case STATE_RECV_PAYLOAD:
        p->buf[p->idx++] = byte;
        if (p->idx == PAYLOAD_SIZE) {
            if (p->buf[IDX_TAIL] == TAIL) {
                /* 小端序: dx = buf[0] | buf[1]<<8 */
                p->target.dx = (int16_t)(((uint16_t)p->buf[1] << 8)
                                        | (uint16_t)p->buf[0]);
                p->target.dy = (int16_t)(((uint16_t)p->buf[3] << 8)
                                        | (uint16_t)p->buf[2]);
                p->target.flag = p->buf[4];
                if (p->target.flag > 1 || p->target.dx < -80 || p->target.dx > 79 ||
                    p->target.dy < -59 || p->target.dy > 60 ||
                    (!p->target.flag && (p->target.dx || p->target.dy))) {
                    uart_parser_fault(p);
                    break;
                }
                p->received_ms = now_ms;
                /* A newer observation replaces the mailbox; any skipped frame
                 * breaks laser qualification, even if the replacement is valid. */
                if (p->frame_ready) p->faults++;
                p->total_frames++;
                p->frame_ready = 1;
                p->state = STATE_SYNC_H1;
            } else {
                p->err_tail++;
                uart_parser_fault(p);
            }
        }
        break;

    }
}

/**
 * @brief  主循环消费最新帧；调用方须屏蔽 RX 中断，避免邮箱读取撕裂。
 * @return 1=有新帧, 0=无
 */
uint8_t uart_parser_consume(uart_parser_t *p, track_target_t *out)
{
    if (p->frame_ready == 0) return 0;

    out->dx   = p->target.dx;
    out->dy   = p->target.dy;
    out->flag = p->target.flag;

    p->frame_ready = 0;
    /* Reception may already be part-way through the next frame. */
    return 1;
}
