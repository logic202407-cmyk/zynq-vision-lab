#include <stdint.h>
#include <stdio.h>
#include <assert.h>
static struct {uint32_t address,value;} regs[512];static unsigned used;
uint32_t *board_test_register(uint32_t a){unsigned i;for(i=0;i<used;i++)if(regs[i].address==a)return &regs[i].value;assert(used<512);regs[used].address=a;return &regs[used++].value;}
#include "board.c"
#include "static_spot.c"
static void fresh(void){used=0;memset(regs,0,sizeof(regs));milliseconds=0;guard_active=guard_event=fault=0;pwm_enabled=0;spot_fired=spot_done=0;spot_started=0;}
int main(void){unsigned i;static_spot_t s={0};
 fresh();board_outputs(1,1500,1500);assert(R(TIM4+0x20)==0&&!pwm_enabled);puts("PASS all requested servo outputs remain off");
 board_laser_set(1);assert(R(0x40021018u)==(1u<<18)&&!spot_fired);puts("PASS no illumination without active guarded session");
 assert(board_guard_refresh(0));board_laser_set(1);assert(R(0x40021018u)==4&&spot_fired);
 for(i=0;i<199;i++)SysTick_Handler();assert(!spot_done);SysTick_Handler();assert(spot_done&&R(0x40021018u)==(1u<<18));board_laser_set(1);assert(R(0x40021018u)==(1u<<18));puts("PASS ISR enforces200ms even without foreground; no retrigger");
 fresh();board_guard_refresh(0);board_laser_set(1);R(GPIOA+0x10)=1;SysTick_Handler();assert(!guard_active&&R(0x40021018u)==(1u<<18));puts("PASS physical key immediately disables illumination");
 fresh();board_guard_refresh(0);milliseconds=450;board_laser_set(1);for(i=0;i<50;i++)SysTick_Handler();assert(!guard_active&&R(0x40021018u)==(1u<<18));puts("PASS communication lease expiry disables illumination");
 fresh();board_guard_refresh(0);board_laser_set(1);board_guard_disarm();assert(R(0x40021018u)==(1u<<18));board_laser_set(1);assert(R(0x40021018u)==(1u<<18));puts("PASS disarm closes pulse");
 assert(!static_spot_tick(&s,0,0,0,0));assert(!static_spot_tick(&s,10,1,4,0));assert(!static_spot_tick(&s,20,1,0,0));assert(!static_spot_tick(&s,1019,1,0,0));assert(static_spot_tick(&s,1020,1,0,0));assert(static_spot_tick(&s,1219,1,0,0));assert(!static_spot_tick(&s,1220,1,0,0));assert(!static_spot_tick(&s,5000,1,0,0));puts("PASS fresh centered stable1s then one200ms pulse");
 memset(&s,0,sizeof(s));static_spot_tick(&s,0,1,0,0);assert(static_spot_tick(&s,1000,1,0,0));assert(!static_spot_tick(&s,1001,0,0,0));assert(!static_spot_tick(&s,5000,1,0,0));puts("PASS target/permit loss during pulse latches it off");
 memset(&s,0,sizeof(s));static_spot_tick(&s,0xffffff00u,1,0,0);assert(static_spot_tick(&s,744u,1,0,0));assert(!static_spot_tick(&s,944u,1,0,0));puts("PASS millisecond wrap bounds pulse");puts("STATIC_SPOT_9_CHECKS_PASS");return 0;}
