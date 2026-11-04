#include <stdint.h>
#include <stdio.h>
#include <assert.h>
static struct {uint32_t address,value;} regs[512];static unsigned used;
uint32_t *board_test_register(uint32_t a){unsigned i;for(i=0;i<used;i++)if(regs[i].address==a)return &regs[i].value;assert(used<512);regs[used].address=a;return &regs[used++].value;}
#include "board.c"
#include "tracking.c"
static void sendbyte(uint32_t uart,uint8_t b){R(uart)=1u<<5;R(uart+4)=b;if(uart==U2)USART2_IRQHandler();else if(uart==0x40011400u)USART6_IRQHandler();else UART5_IRQHandler();}
int main(void){uint8_t b;uint32_t ts;unsigned i,j;vision_parser_t p[3];tracking_t t[3];uint32_t ports[3]={U2,0x40011400u,0x40005000u};uint8_t packets[3][8]={{0xaa,0xff,11,0,12,0,1,0xee},{0xaa,0xff,21,0,22,0,1,0xee},{0xaa,0xff,31,0,32,0,1,0xee}};
 for(i=0;i<3;i++){vision_init(&p[i]);tracking_init(&t[i]);}
 extra_rx_init();assert(R(0x40010020u)==0&&R(0x40010044u)==0);assert(R(0x40011408u)==139&&R(0x40005008u)==139);puts("PASS baud and TIM1 off");
 for(j=0;j<8;j++)for(i=0;i<3;i++)sendbyte(ports[i],packets[i][j]);
 for(i=0;i<3;i++){while(board_camera_byte(i,&b,&ts))vision_feed(&p[i],&t[i],b,ts,0);assert(t[i].dx==(int)(11+10*i)&&t[i].dy==(int)(12+10*i));assert(!t[i].outputs);}puts("PASS interleaved packets no cross-talk");
 for(i=0;i<3;i++){tracking_tick(&t[i],201);assert(!t[i].valid&&!t[i].outputs);}puts("PASS stale data invalid");
 assert(!board_camera_byte(3,&b,&ts));puts("PASS invalid source");
 board_guard_refresh(0);board_laser_set(1);board_outputs(1,1500,1500);assert(R(0x40021018u)==(1u<<18)&&R(TIM4+0x20)==0);puts("PASS requests cannot enable outputs");
 for(i=0;i<256;i++)sendbyte(0x40011400u,0xaa);assert(fault&&guard_event==BOARD_GUARD_UART);assert(!board_camera_byte(2,&b,&ts));puts("PASS overflow isolated and trips fault");return 0;}
