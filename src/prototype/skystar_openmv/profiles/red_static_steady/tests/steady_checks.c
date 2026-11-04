#include <stdint.h>
#include <stdio.h>
#include <assert.h>
static struct {uint32_t address,value;} regs[512];static unsigned used;
uint32_t *board_test_register(uint32_t a){unsigned i;for(i=0;i<used;i++)if(regs[i].address==a)return &regs[i].value;assert(used<512);regs[used].address=a;return &regs[used++].value;}
#include "board.c"
#include "static_spot.c"
static void fresh(void){used=0;memset(regs,0,sizeof(regs));milliseconds=0;guard_active=guard_event=fault=0;pwm_enabled=0;}
int main(void){unsigned i;static_spot_t s={0};
 fresh();board_outputs(1,1500,1500);assert(R(TIM4+0x20)==0&&!pwm_enabled);puts("PASS servo output forced off");
 board_laser_set(1);assert(R(0x40021018u)==(1u<<18));puts("PASS unarmed dark");
 assert(board_guard_refresh(0));board_laser_set(1);
 for(i=0;i<120000;i++){if(i%100==0)assert(board_guard_refresh(milliseconds));SysTick_Handler();board_laser_set(1);assert(R(0x40021018u)==4);assert(!pwm_enabled);}puts("PASS continuous 120s with fresh lease, no 200ms cutoff");
 R(GPIOA+0x10)=1;SysTick_Handler();assert(!guard_active&&R(0x40021018u)==(1u<<18));board_laser_set(1);assert(R(0x40021018u)==(1u<<18));puts("PASS key ISR closes and prevents restart");
 fresh();board_guard_refresh(0);board_laser_set(1);for(i=0;i<500;i++)SysTick_Handler();assert(!guard_active&&R(0x40021018u)==(1u<<18));puts("PASS lease ISR expiry off at 500ms without foreground");
 fresh();board_guard_refresh(0);board_laser_set(1);board_guard_disarm();board_laser_set(1);assert(R(0x40021018u)==(1u<<18));puts("PASS disarm off");
 fresh();board_guard_refresh(0);R(TIM4+0x20)=1;board_laser_set(1);assert(R(0x40021018u)==(1u<<18));puts("PASS actual PWM conflict blocks light");
 assert(!static_spot_tick(&s,0,0,0,0));assert(!static_spot_tick(&s,1,1,0,10));assert(!static_spot_tick(&s,1000,1,0,10));assert(static_spot_tick(&s,1001,1,0,10));assert(static_spot_tick(&s,120001,1,0,10));puts("PASS stable target starts without centering and stays on");
 assert(!static_spot_tick(&s,120002,0,0,10));assert(!static_spot_tick(&s,130002,1,0,10));puts("PASS lost target latches off, no automatic restart");
 memset(&s,0,sizeof(s));assert(!static_spot_tick(&s,0xffffff00u,1,0,10));assert(static_spot_tick(&s,744u,1,0,10));puts("PASS tick wrap");
 puts("STEADY_10_CHECKS_PASS");return 0;}
