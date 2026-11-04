#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
static struct {uint32_t address,value;} regs[512];static unsigned used;
uint32_t *board_test_register(uint32_t a){unsigned i;for(i=0;i<used;i++)if(regs[i].address==a)return &regs[i].value;assert(used<512);regs[used].address=a;return &regs[used++].value;}
#include "board.c"
static void ready(void){memset(regs,0,sizeof(regs));used=0;guard_active=guard_event=fault=0;pwm_enabled=0;milliseconds=100;static_laser_mask=0;assert(board_guard_refresh(milliseconds));}
static void off(void){assert((R(0x40021018u)&(3u<<18))==(3u<<18));assert(!(R(0x40021018u)&12));}
int main(void){unsigned i,n;
 ready();board_laser_set(1);off();puts("PASS boot selection cannot illuminate");
 for(i=1;i<=3;i++){ready();static_laser_mask=i;board_laser_set(1);assert(R(0x40021018u)==((i<<2)|((3u^i)<<18)));}puts("PASS red/yellow/both atomic selections");
 ready();static_laser_mask=4;board_laser_set(1);off();puts("PASS invalid selection rejected");
 ready();static_laser_mask=3;board_laser_set(0);off();puts("PASS explicit disable");
 ready();static_laser_mask=3;board_guard_disarm();board_laser_set(1);off();puts("PASS STOP disarms both");
 ready();static_laser_mask=3;board_laser_set(1);for(n=0;n<500;n++)SysTick_Handler();assert(guard_event==BOARD_GUARD_LEASE);off();board_laser_set(1);off();puts("PASS missing heartbeat shuts off and cannot reenable");
 ready();static_laser_mask=3;R(GPIOA+0x10)=1;SysTick_Handler();off();assert(guard_event==BOARD_GUARD_KEY);puts("PASS physical button disables both");
 ready();static_laser_mask=3;R(U2)=1;USART2_IRQHandler();off();assert(guard_event==BOARD_GUARD_UART);puts("PASS UART error disables both");
 for(i=0;i<3;i++){ready();static_laser_mask=3;if(i==0)R(TIM4+0x20)=1;else if(i==1)R(0x40010020u)=1;else R(0x40010044u)=1u<<15;board_laser_set(1);off();}puts("PASS PWM and TIM1 master enable block illumination");
 ready();static_laser_mask=3;board_outputs(1,1500,1500);assert(R(TIM4+0x20)==0&&R(0x40010020u)==0&&R(0x40010044u)==0);for(i=12;i<=15;i++)assert(((R(GPIOD)>>(2*i))&3)==1);off();puts("PASS all six servo outputs remain disabled");
 ready();static_laser_mask=3;board_laser_set(1);board_guard_disarm();for(i=0;i<used;i++)assert(regs[i].address<0x40020400u||regs[i].address>=0x40020800u);puts("PASS no third-laser GPIOB access");
 return 0;}
