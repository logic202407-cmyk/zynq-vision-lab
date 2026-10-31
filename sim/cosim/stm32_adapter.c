/* Test-only shared library. Execute the unchanged v15 source, no hardware I/O. */
#include <stdint.h>
#include <string.h>
#include <assert.h>
#include "tracking.h"
static struct { uint32_t address,value; } regs[256];
static unsigned nr,rng_reads;
uint32_t *board_test_register(uint32_t address) {
    unsigned i;
    for(i=0;i<nr;i++) if(regs[i].address==address) {
        if(address==0x40023800u) {
            regs[i].value|=2u;
            if(regs[i].value&(1u<<24)) regs[i].value|=1u<<25;
            else regs[i].value&=~(1u<<25);
        }
        if(address==0x50060804u) regs[i].value=1;
        if(address==0x50060808u) regs[i].value=0x12340000u+(++rng_reads);
        return &regs[i].value;
    }
    assert(nr<256);regs[nr++].address=address;return board_test_register(address);
}
#include "board.c"
#define main firmware_entry
#include "main.c"
#undef main
#define API __declspec(dllexport)
static uint32_t last_status;
API void model_init(void) {
    uint32_t hi,lo;int ok;
    memset(regs,0,sizeof(regs));nr=rng_reads=0;
    used=dropping=command_last_ms=tx_dropped=last_status=0;
    tracking_init(&control);vision_init(&parser);board_init();
    ok=board_session_nonce(&hi,&lo);safety_init(&guardian,hi,lo,ok);
    (void)board_send("SKYSTAR F407 v15 GUARDED_SESSION HSI16 PWM_OFF CONSOLE=" CONSOLE_LABEL "\r\n");
}
API void model_tick(void) { SysTick_Handler(); }
API void model_receive(unsigned byte,unsigned bad_stop) {
    R(U3)= (1u<<5)|(bad_stop ? 2u:0u);R(U3+4)=byte;
    USART3_IRQHandler();R(U3)=0; /* modeled SR/DR read clears RX flags */
}
API void model_foreground(void) {
    unsigned n;uint8_t byte;uint32_t received,now=board_ms();
    poll_safety(now);console_expire(now);
    for(n=0;n<32 && board_pc_timed_byte(&byte,&received);n++)
        console_feed(byte,received,board_ms());
    for(n=0;n<64 && board_vision_byte(&byte,&received);n++)
        vision_byte(byte,received,board_ms());
    now=board_ms();poll_safety(now);tracking_tick(&control,now);
    board_outputs(safety_armed(&guardian)&&control.outputs,control.pan_us,control.tilt_us);
    if((uint32_t)(now-last_status)>=100u) { last_status=now;status(); }
}
API int model_transmit(void) {
    unsigned before=tx_tail;
    R(U3)|=1u<<7;board_poll_tx();R(U3)&=~(1u<<7);
    return before!=tx_tail ? (int)(R(U3+4)&255u) : -1;
}
API unsigned model_reg(unsigned address) { return R(address); }
API unsigned model_state(void) { return guardian.state; }
API unsigned model_reason(void) { return guardian.reason; }
API unsigned model_live(void) { return guardian.live_ms; }
