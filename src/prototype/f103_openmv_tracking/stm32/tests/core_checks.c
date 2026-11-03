#include "laser_lock.h"
#include "uart_parser.h"
#include "pid.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks;
#define CHECK(x) do { ++checks; if (!(x)) { printf("FAIL line %u: %s\n", __LINE__, #x); exit(1); } } while (0)

static void frame(uart_parser_t *p, int16_t dx, int16_t dy, uint8_t flag, uint8_t tail, uint32_t ms)
{
    uint8_t data[8] = {0xAA, 0xFF, (uint8_t)dx, (uint8_t)((uint16_t)dx>>8),
                      (uint8_t)dy, (uint8_t)((uint16_t)dy>>8), flag, tail};
    unsigned i;
    for (i=0;i<8;i++) uart_parser_feed(p,data[i],ms);
}
int main(void)
{
    laser_lock_t s;
    uart_parser_t p;
    track_target_t target;
    pid_t pid;
    uint32_t faults;
    unsigned i;
    laser_lock_reset(&s);
    CHECK(!laser_lock_tick(&s, 1000, 1));
    /* First valid frame turns on immediately, with no dwell time. */
    laser_lock_frame(&s, 1000, 1);
    CHECK(laser_lock_tick(&s, 1000, 1));
    CHECK(laser_lock_tick(&s, 1199, 1));
    CHECK(!laser_lock_tick(&s, 1200, 1));
    CHECK(!laser_lock_tick(&s, 1201, 1));
    laser_lock_frame(&s, 1201, 1);
    CHECK(laser_lock_tick(&s, 1201, 1));
    laser_lock_frame(&s, 1210, 0);
    CHECK(!laser_lock_tick(&s, 1210, 1));
    laser_lock_frame(&s, 1220, 2);
    CHECK(!laser_lock_tick(&s, 1220, 1));
    laser_lock_frame(&s, 1300, 1);
    CHECK(laser_lock_tick(&s, 1300, 1));
    CHECK(!laser_lock_tick(&s, 1301, 0));
    CHECK(!laser_lock_tick(&s, 1302, 1));
    laser_lock_frame(&s, 1310, 1);
    CHECK(laser_lock_tick(&s, 1310, 1));
    /* A newly consumed but already stale observation cannot light PB0. */
    laser_lock_frame(&s, 1400, 1);
    CHECK(!laser_lock_tick(&s, 1600, 1));
    laser_lock_frame(&s, UINT32_MAX-99u, 1);
    CHECK(laser_lock_tick(&s, UINT32_MAX-99u, 1));
    CHECK(laser_lock_tick(&s, 99u, 1));
    CHECK(!laser_lock_tick(&s, 100u, 1));

    /* Off-center target frames and changing coordinates still turn on. */
    uart_parser_init(&p);
    frame(&p,-80,60,1,0xEE,10);
    CHECK(uart_parser_consume(&p,&target));
    laser_lock_frame(&s,p.received_ms,target.flag);
    CHECK(laser_lock_tick(&s,10,1));
    frame(&p,79,-59,1,0xEE,20);
    CHECK(uart_parser_consume(&p,&target));
    laser_lock_frame(&s,p.received_ms,target.flag);
    CHECK(laser_lock_tick(&s,20,1));
    frame(&p,0,0,0,0xEE,30);
    CHECK(uart_parser_consume(&p,&target));
    laser_lock_frame(&s,p.received_ms,target.flag);
    CHECK(!laser_lock_tick(&s,30,1));

    uart_parser_init(&p);
    frame(&p,-80,60,1,0xEE,100);
    CHECK(uart_parser_consume(&p,&target));
    CHECK(target.dx==-80 && target.dy==60 && target.flag==1 && p.received_ms==100);
    CHECK(!uart_parser_consume(&p,&target));
    frame(&p,79,-59,1,0xEE,110);
    CHECK(uart_parser_consume(&p,&target) && target.dx==79 && target.dy==-59);
    frame(&p,0,0,0,0xEE,120);
    CHECK(uart_parser_consume(&p,&target) && !target.flag);
    faults=p.faults;
    frame(&p,80,0,1,0xEE,130);
    frame(&p,0,-60,1,0xEE,140);
    frame(&p,0,0,2,0xEE,150);
    frame(&p,1,0,0,0xEE,160);
    frame(&p,0,0,1,0,170);
    CHECK(p.faults==faults+5 && !p.frame_ready);
    uart_parser_feed(&p,0xAA,200);
    uart_parser_feed(&p,0xFF,200);
    uart_parser_expire(&p,219);
    CHECK(p.state==STATE_RECV_PAYLOAD);
    uart_parser_expire(&p,220);
    CHECK(p.state==STATE_SYNC_H1 && p.faults==faults+6);
    frame(&p,0,0,1,0xEE,230);
    frame(&p,0,0,0,0xEE,240);
    CHECK(p.faults==faults+7 && uart_parser_consume(&p,&target) && !target.flag);
    frame(&p,0,0,1,0xEE,250);
    uart_parser_feed(&p,0xAA,251);
    uart_parser_feed(&p,0xFF,251);
    CHECK(uart_parser_consume(&p,&target) && p.state==STATE_RECV_PAYLOAD);
    for (i=0;i<4;i++) uart_parser_feed(&p,0,252);
    uart_parser_feed(&p,1,252); uart_parser_feed(&p,0xEE,252);
    CHECK(uart_parser_consume(&p,&target) && target.flag);
    frame(&p,0,0,1,0xEE,260);
    uart_parser_fault(&p);
    CHECK(!p.frame_ready && !uart_parser_consume(&p,&target));
    uart_parser_feed(&p,0xAA,UINT32_MAX-5u);
    uart_parser_expire(&p,14u);
    CHECK(p.state==STATE_SYNC_H1);

    pid_init(&pid,3.0f,0.5f,0,-750,750);
    CHECK(pid_update(&pid,0,-20,0.02f)>60.0f);
    pid_reset(&pid);
    CHECK(pid.integral==0 && pid.prev_error==0);
    CHECK(pid_update(&pid,0,-10000,0.02f)==750.0f);
    printf("PASS %u assertions: detection gate, loss, disable, timeout, rollover, parser and PID\n",checks);
    return 0;
}
