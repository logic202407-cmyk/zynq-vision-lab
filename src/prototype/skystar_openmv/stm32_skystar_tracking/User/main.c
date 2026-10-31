#include "board.h"
#include "tracking.h"
#include <stdio.h>
#include <string.h>

static tracking_t control;
static vision_parser_t parser;
static char line[64];
static unsigned used, dropping;
static void flush_vision(void) { board_flush_vision(); vision_init(&parser); }
static void status(void)
{
    char text[400];
    const char *state=control.valid ? "tracking" : "waiting";
    /* P0-style PC status only: FRAME is a locally counted legacy frame;
       SESSION=1 and SOURCE_MS=0 are local labels, not camera wire fields. */
    sprintf(text,"P0V 1 STATE %s MODE %s VALID %u ENABLED %u DX %d DY %d PAN %u TLT %u REQ_PAN %u REQ_TLT %u SESSION 1 FRAME %lu RX_MS %lu SOURCE_MS 0 REJECT none BAD %lu PARSE_BAD %lu PKP %ld PKI %ld PKD %ld TKP %ld TKI %ld TKD %ld\r\n",
        state,control.automatic ? "auto":"manual",control.valid,control.outputs,
        control.dx,control.dy,control.pan_us,control.tilt_us,control.pan_us,control.tilt_us,
        (unsigned long)control.frames,(unsigned long)control.received_ms,
        (unsigned long)control.rejected,(unsigned long)control.rejected,
        (long)(control.pan_pid.Kp*100+0.5f),(long)(control.pan_pid.Ki*100+0.5f),
        (long)(control.pan_pid.Kd*100+0.5f),(long)(control.tilt_pid.Kp*100+0.5f),
        (long)(control.tilt_pid.Ki*100+0.5f),(long)(control.tilt_pid.Kd*100+0.5f));
    (void)board_send(text);
}
/* UART arrival timestamps prevent old fragments becoming a new motion command. */
#define COMMAND_TIMEOUT_MS 200u
static uint32_t command_last_ms;
static void console_expire(uint32_t now)
{
    if (used && (uint32_t)(now-command_last_ms)>=COMMAND_TIMEOUT_MS) {
        used=0; dropping=1; tracking_stop(&control); flush_vision();
    }
}
static void console_feed(uint8_t byte, uint32_t received, uint32_t now)
{
    console_expire(received);
    if ((uint32_t)(now-received)>=COMMAND_TIMEOUT_MS) {
        used=0; dropping=1; tracking_stop(&control); flush_vision();
    }
    command_last_ms=received;
    if (byte=='\r' || byte=='\n') {
        if (used || dropping) {
            line[used]=0;
            if (!dropping && !board_button()) {
                /* Discard queued observations before any mode/manual command. */
                if (strcmp(line,"st"))
                    flush_vision();
                if (!tracking_command(&control,line)) (void)board_send("ERROR command\r\n");
                status();
            } else (void)board_send("ERROR command overflow or KEY held\r\n");
            used=dropping=0;
        }
    } else if (!dropping && byte>=32 && byte<=126 && used<sizeof(line)-1) {
        if (byte>='A' && byte<='Z') byte=(uint8_t)(byte+'a'-'A');
        line[used++]=(char)byte;
    } else dropping=1;
}
int main(void)
{
    uint32_t last_status=0;
    uint8_t byte;
    uint32_t received;
    tracking_init(&control); vision_init(&parser); board_init();
    (void)board_send("SKYSTAR F407 TRACKING 2026-10-31 v14 TIMED_CONSOLE HOLD_PID_BASE HSI16 PWM_OFF VISION=PA3 PAN=PD12 TILT=PD13 CONSOLE=" CONSOLE_LABEL "\r\n");
    for (;;) {
        unsigned count;
        uint32_t now=board_ms();
        if (board_take_fault()) {
            tracking_stop(&control); flush_vision(); used=dropping=0;
            (void)board_send("ERROR UART; PWM_OFF; send auto/home explicitly\r\n");
        }
        if (board_button()) { tracking_stop(&control); flush_vision(); }
        console_expire(now);
        for (count=0;count<32 && board_pc_timed_byte(&byte,&received);++count)
            console_feed(byte,received,board_ms());
        now=board_ms();
        for (count=0;count<64 && board_vision_byte(&byte,&received);++count)
            (void)vision_feed(&parser,&control,byte,received,board_ms());
        now=board_ms();
        if (parser.used && (uint32_t)(now-parser.last_ms)>=BYTE_TIMEOUT_MS) {
            vision_init(&parser); tracking_reject(&control);
        }
        tracking_tick(&control,now);
        if (board_button()) tracking_stop(&control);
        board_outputs(control.outputs,control.pan_us,control.tilt_us);
        if ((uint32_t)(now-last_status)>=100u) { last_status=now; status(); }
        board_poll_tx();
    }
}
