/* Execute the production controller/PID and the production driver with fake
 * registers. This cannot prove actual UART timing, PWM or servo motion. */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "tracking.h"

static struct { uint32_t address, value; } registers[256];
static unsigned register_count;
uint32_t *board_test_register(uint32_t address)
{
    unsigned i;
    for (i=0;i<register_count;++i) if (registers[i].address==address) return &registers[i].value;
    assert(register_count<256);
    registers[register_count].address=address;
    return &registers[register_count++].value;
}
#include "../User/board.c"
#define main firmware_entry
#include "../User/main.c"
#undef main

static unsigned checks;
#define CHECK(x) do { assert(x); ++checks; } while (0)
static void packet(vision_parser_t *p, tracking_t *c, int dx, int dy,
                   unsigned valid, uint32_t time)
{
    uint8_t bytes[8]={0xAA,0xFF,(uint8_t)dx,(uint8_t)(dx>>8),
                     (uint8_t)dy,(uint8_t)(dy>>8),(uint8_t)valid,0xEE};
    unsigned i;
    for (i=0;i<8;++i) (void)vision_feed(p,c,bytes[i],time,time);
}
static void controller_checks(void)
{
    tracking_t c;
    vision_parser_t p;
    unsigned n;
    /* PAN reaches the new 25 ms and long-frame slew limits, without exceeding them. */
    { tracking_t s; uint16_t old;
      tracking_init(&s); tracking_auto(&s);
      tracking_observe(&s,79,0,1,100,100);
      old=s.pan_us;
      tracking_observe(&s,79,0,1,125,125);
      CHECK(s.pan_us-old==8);
      old=s.pan_us;
      tracking_observe(&s,79,0,1,225,225);
      CHECK(s.pan_us-old==15);
    }
    /* Holding near centre and losing vision must preserve the last output baseline. */
    { tracking_t s; uint16_t pan, tilt;
      tracking_init(&s); tracking_auto(&s); s.outputs=1;
      s.pan_us=1600; s.tilt_us=1400;
      tracking_observe(&s,0,0,1,100,100);
      CHECK(s.pan_us==1600 && s.tilt_us==1400);
      CHECK(s.pan_pid.integral==100 && s.tilt_pid.integral==-100);
      tracking_observe(&s,0,0,0,125,125);
      pan=s.pan_us; tilt=s.tilt_us;
      CHECK(!s.valid && s.outputs && pan==1600 && tilt==1400);
      tracking_observe(&s,10,-10,1,150,150);
      CHECK(s.valid && s.outputs && s.pan_us>=pan && s.pan_us-pan<=3);
      CHECK(s.tilt_us<=tilt && tilt-s.tilt_us<=3);
      tracking_observe(&s,0,0,0,175,175);
      pan=s.pan_us; tilt=s.tilt_us;
      tracking_observe(&s,0,0,1,200,200);
      CHECK(s.pan_us==pan && s.tilt_us==tilt);
    }
    /* Simplified static target model: sign and eventual convergence, not physical proof. */
    { tracking_t s; unsigned i; int x=20,y=15;
      tracking_init(&s); tracking_auto(&s);
      s.pan_pid.Kp=3.5f; s.pan_pid.Ki=0.8f;
      s.tilt_pid.Kp=3.0f; s.tilt_pid.Ki=0.3f;
      for (i=0;i<2000;++i) {
          x=(int)(20.0f-0.276f*((int)s.pan_us-1500));
          y=(int)(15.0f-0.2f*((int)s.tilt_us-1500));
          tracking_observe(&s,(int16_t)x,(int16_t)y,1,100+25*i,100+25*i);
      }
      CHECK(abs(x)<=4 && abs(y)<=4);
    }
    tracking_init(&c); vision_init(&p);
    CHECK(!c.outputs && !c.automatic);
    CHECK(c.pan_pid.Kp==3 && c.pan_pid.Ki==0.5f && c.tilt_pid.Ki==0.8f);
    packet(&p,&c,20,-10,1,1);
    CHECK(c.valid && !c.outputs && c.dx==20 && c.dy==-10);
    CHECK(tracking_command(&c,"auto"));
    CHECK(!c.outputs && !c.valid);
    packet(&p,&c,0,0,0,10); CHECK(!c.valid && !c.outputs);
    packet(&p,&c,20,-10,1,25);
    CHECK(c.outputs && c.pan_us>PAN_HOME_US && c.tilt_us<TILT_HOME_US);
    /* Independent measured plant slopes: dx/du=-6.9/25, dy/du=-5/25.
       A first correction must reduce squared error on this physical mount. */
    { float x=20.0f-6.9f/25.0f*((float)c.pan_us-PAN_HOME_US);
      float y=-10.0f-5.0f/25.0f*((float)c.tilt_us-TILT_HOME_US);
      CHECK(x*x<400.0f && y*y<100.0f);
    }
    tracking_tick(&c,224); CHECK(c.valid);
    { uint16_t pan=c.pan_us, tilt=c.tilt_us;
      tracking_tick(&c,225); CHECK(!c.valid && c.outputs && c.automatic);
      CHECK(c.pan_us==pan && c.tilt_us==tilt);
      tracking_tick(&c,1000); CHECK(c.outputs && c.pan_us==pan && c.tilt_us==tilt);
    }
    packet(&p,&c,-80,60,1,250);
    CHECK(c.valid && c.outputs);
    CHECK(c.pan_us>=PAN_MIN_US && c.pan_us<=PAN_MAX_US);
    CHECK(c.tilt_us>=TILT_MIN_US && c.tilt_us<=TILT_MAX_US);
    { uint16_t pan=c.pan_us, tilt=c.tilt_us;
      packet(&p,&c,0,0,0,275);
      CHECK(!c.valid && c.outputs && c.pan_us==pan && c.tilt_us==tilt);
    }
    packet(&p,&c,0,0,1,300); CHECK(c.valid && c.outputs);
    CHECK(tracking_command(&c,"stop"));
    packet(&p,&c,30,30,1,325); CHECK(!c.outputs && !c.automatic);
    CHECK(tracking_command(&c,"home") && c.outputs && c.pan_us==1500 && c.tilt_us==1500);
    CHECK(tracking_command(&c,"pan 1500") && c.pan_us==1500 && c.tilt_us==1500);
    CHECK(tracking_command(&c,"tlt 1700") && c.pan_us==1500 && c.tilt_us==1700);
    CHECK(!tracking_command(&c,"tlt 1701") && !tracking_command(&c,"tlt 1299"));
    CHECK(tracking_command(&c,"tlt 1300") && c.tilt_us==1300);
    for (n=0;n<10;++n) {
        const char *bad[]={"pan 2400","tlt 1200","pan 1450.5","pkp nan","pkp 51", "pkp -1", "pkp 2x", "pkp .", "auto junk", "pkp 999999999999999"};
        CHECK(!tracking_command(&c,bad[n]));
    }
    CHECK(tracking_command(&c,"pkp 4.25") && c.pan_pid.Kp==4.25f);
    tracking_auto(&c); packet(&p,&c,79,-59,1,350);
    for (n=0;n<100;++n) packet(&p,&c,79,-59,1,375+25*n);
    CHECK(c.outputs && c.pan_us<=1700 && c.tilt_us==1300);
    tracking_auto(&c);
    for (n=0;n<100;++n) packet(&p,&c,0,60,1,3000+25*n);
    CHECK(c.outputs && c.tilt_us==1700);
    CHECK(c.pan_pid.integral<=200 && c.pan_pid.integral>=-200);
    CHECK(c.tilt_pid.integral<=200 && c.tilt_pid.integral>=-200);
    for (n=0;n<200;++n) packet(&p,&c,0,-59,1,5500+25*n);
    CHECK(c.outputs && c.tilt_us<1500);
    { uint16_t previous=c.tilt_us, previous_pan=c.pan_us;
      for (n=0;n<20;++n) {
          packet(&p,&c,79,60,1,10500+25*n);
          CHECK((int)c.tilt_us-(int)previous<=8 && (int)previous-(int)c.tilt_us<=8);
          CHECK((int)c.pan_us-(int)previous_pan<=8 && (int)previous_pan-(int)c.pan_us<=8);
          previous=c.tilt_us;
          previous_pan=c.pan_us;
      }
    }
    packet(&p,&c,80,0,1,3000); CHECK(!c.valid && !c.outputs);
    packet(&p,&c,0,-60,1,3025); CHECK(!c.valid && !c.outputs);
    packet(&p,&c,0,0,2,3050); CHECK(!c.valid && !c.outputs);
    packet(&p,&c,1,0,0,3075); CHECK(!c.valid && !c.outputs);
    tracking_observe(&c,0,0,1,3100,3300); CHECK(!c.valid);
    /* Counter wrap uses unsigned duration arithmetic. */
    packet(&p,&c,20,0,1,0xFFFFFFF0u);
    tracking_tick(&c,0xB7u); CHECK(c.valid);
    tracking_tick(&c,0xB8u); CHECK(!c.valid && c.outputs);
    tracking_stop(&c); CHECK(!c.outputs && !c.automatic);
    /* Pure PID integral has a time base and Ki=0 clears prior history. */
    { pid_t a,b; unsigned i;
      pid_init(&a,0,0.5f,0,-750,750); pid_init(&b,0,0.5f,0,-750,750);
      for(i=0;i<100;++i) (void)pid_update(&a,10,0,0.01f);
      for(i=0;i<50;++i) (void)pid_update(&b,10,0,0.02f);
      CHECK(fabsf(a.integral-b.integral)<0.001f);
      a.Ki=0; (void)pid_update(&a,10,0,0.02f); CHECK(a.integral==0);
    }
}
static void parser_checks(void)
{
    tracking_t c; vision_parser_t p; unsigned i;
    const uint8_t truncated[]={0xAA,0xFF,1,0,0xAA,0xFF,20,0,0,0,1,0xEE};
    tracking_init(&c); tracking_auto(&c); vision_init(&p);
    for(i=0;i<sizeof(truncated);++i) (void)vision_feed(&p,&c,truncated[i],1,1);
    CHECK(c.valid && c.dx==20 && c.rejected==1);
    vision_init(&p);
    (void)vision_feed(&p,&c,0xAA,10,10);
    (void)vision_feed(&p,&c,0xFF,30,30);
    CHECK(!c.valid && !c.outputs && p.used==0);
    packet(&p,&c,-1,1,1,35); CHECK(c.valid && c.dx==-1 && c.dy==1);
    vision_init(&p);
    (void)vision_feed(&p,&c,0xAA,40,40);
    packet(&p,&c,5,5,1,40); CHECK(c.valid && c.dx==5);
}
static void driver_checks(void)
{
    uint8_t b; uint32_t t; unsigned i;
    R(RCC)=3; board_init();
    CHECK(R(CONSOLE+8)==139 && R(U2+8)==139);
    CHECK(R(TIM4+0x28)==15 && R(TIM4+0x2C)==19999);
    CHECK(R(TIM4+0x20)==0 && !pwm_enabled);
    CHECK((R(GPIOD) & (255u<<24))==(85u<<24));
    CHECK(((R(GPIOA+0x20)>>12)&15u)==7u); /* PA3 AF7 */
    #if CONSOLE_USART == 3
    CHECK((R(0xE000E104u)&192u)==192u);
    CHECK(((R(GPIOC+0x24)>>8)&255u)==0x77u);
    CHECK((R(RCC+0x30)&4u)!=0);
    CHECK((R(RCC+0x40)&(1u<<18))!=0);
#else
    CHECK((R(0xE000E104u)&96u)==96u);
#endif
    CHECK(R(0xE000E014u)==15999);
    board_outputs(1,1500,1550);
    CHECK(R(TIM4+0x34)==1500 && R(TIM4+0x38)==1550);
    CHECK(R(TIM4+0x20)==17 && (R(TIM4+0x20)&0x1100u)==0);
    CHECK(((R(GPIOD+0x24)>>16)&255u)==0x22u);
    board_outputs(0,1500,1550); CHECK(R(TIM4+0x20)==0 && !pwm_enabled);
    milliseconds=12; R(U2)=32; R(U2+4)=0xAA; USART2_IRQHandler();
    CHECK(board_vision_byte(&b,&t) && b==0xAA && t==12);
    CHECK(!board_vision_byte(&b,&t));
    /* On queue full or hardware receive error, fail instead of silently overwrite. */
    for(i=0;i<256;++i) { R(U2)=32; R(U2+4)=i; USART2_IRQHandler(); }
    CHECK(board_take_fault()); CHECK(!board_vision_byte(&b,&t));
    R(CONSOLE)=8; R(CONSOLE+4)=1;
#if CONSOLE_USART == 3
    USART3_IRQHandler();
#else
    USART1_IRQHandler();
#endif
 CHECK(board_take_fault());
    milliseconds=13; R(CONSOLE)=32; R(CONSOLE+4)='s';
#if CONSOLE_USART == 3
    USART3_IRQHandler();
#else
    USART1_IRQHandler();
#endif
    CHECK(board_pc_timed_byte(&b,&t) && b=='s' && t==13);
    CHECK(!board_pc_timed_byte(&b,&t));
    CHECK(board_send("ABC")); R(CONSOLE)=128;
    board_poll_tx(); CHECK(R(CONSOLE+4)=='A');
    board_poll_tx(); CHECK(R(CONSOLE+4)=='B');
    board_poll_tx(); CHECK(R(CONSOLE+4)=='C');
    R(GPIOA+0x10)=1; CHECK(board_button());
    R(GPIOA+0x10)=0; CHECK(!board_button());
}
static void command_text(const char *s, uint32_t rx, uint32_t now)
{
    while (*s) console_feed((uint8_t)*s++,rx,now);
}
static void command_checks(void)
{
    tracking_init(&control); used=dropping=0; tx_head=tx_tail=0;
    command_text("pan 1600\n",10,10); CHECK(control.outputs && control.pan_us==1600);
    command_text("pan 1",20,20); console_expire(220);
    CHECK(!control.outputs && dropping && !used);
    command_text("600\n",221,221); CHECK(!control.outputs && control.pan_us==1600);
    command_text("home\n",222,222); CHECK(control.outputs && control.pan_us==1500);
    command_text("pan 1650\n",230,430); CHECK(!control.outputs && control.pan_us==1500);
    command_text("pan 1550\n",431,431); CHECK(control.outputs && control.pan_us==1550);
    command_text("stop\n",432,432); CHECK(!control.outputs);
    command_text("pan 1",0xFFFFFFF0u,0xFFFFFFF0u);
    console_expire(0xB7u); CHECK(used && !dropping);
    console_expire(0xB8u); CHECK(!used && dropping && !control.outputs);
    command_text("600\n",0xB9u,0xB9u); CHECK(!control.outputs);
    command_text("home\r\n",0xBAu,0xBAu); CHECK(control.outputs && !used && !dropping);
    command_text("PAN 1510\n",0xBBu,0xBBu); CHECK(control.pan_us==1510);
    R(GPIOA+0x10)=1; command_text("home\n",0xBCu,0xBCu); CHECK(control.pan_us==1510);
    R(GPIOA+0x10)=0;
}
int main(void)
{
    controller_checks(); parser_checks(); driver_checks(); command_checks();
    tracking_init(&control); tx_head=tx_tail=0; status();
    CHECK(strstr(tx,"P0V 1 STATE waiting MODE manual VALID 0 ENABLED 0")!=0);
    CHECK(strstr(tx,"PKP 300 PKI 50 PKD 0 TKP 500 TKI 80 TKD 0")!=0);
    tx[tx_head]=0; printf("TELEMETRY %s",tx);
    printf("PASS %u assertions: actual PID/controller/parser and driver register model; hardware not tested\n", checks);
    return 0;
}
