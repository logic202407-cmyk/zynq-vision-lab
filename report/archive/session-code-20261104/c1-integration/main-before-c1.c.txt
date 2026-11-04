#include "board.h"
#include "tracking.h"
#include "safety.h"
#include <stdio.h>
#include <string.h>

static tracking_t control;
static vision_parser_t parser;
static safety_t guardian;
static char line[SAFETY_LINE_BYTES];
static unsigned used, dropping;
static uint32_t command_last_ms, tx_dropped;
static void flush_vision(void) { board_flush_vision(); vision_init(&parser); }
static void disarm_queues(void)
{
    board_guard_disarm(); flush_vision(); board_flush_pc(); used=dropping=0;
}
static void trip(safe_reason_t reason)
{
    safety_trip(&guardian,&control,reason); disarm_queues();
}
static void poll_safety(uint32_t now);
#ifdef S1ACK1
#include "s1ack.h"
#endif
static void status(void)
{
    char text[512]; int n;
#ifdef S1ACK1
    /* Keep at least 256 bytes for one transaction response. */
    if (board_tx_free()<384u) return;
    n=snprintf(text,sizeof(text),"S1STAT SAFE %s WHY %s NONCE %08lx%08lx SEQ %lu TX_DROP %lu FW 15 CAP S1ACK1\r\n",
        safety_state_name(&guardian),safety_reason_name(&guardian),
        (unsigned long)guardian.nonce_hi,(unsigned long)guardian.nonce_lo,
        (unsigned long)guardian.sequence,(unsigned long)tx_dropped);
    if(n<0 || n>=128 || !board_send(text)) ++tx_dropped;
    return;
#endif
    /* FRAME is local to legacy vision reception, not an end-to-end frame ID. */
    n=snprintf(text,sizeof(text),"P0V 1 STATE %s MODE %s VALID %u ENABLED %u DX %d DY %d PAN %u TLT %u REQ_PAN %u REQ_TLT %u SESSION 1 FRAME %lu RX_MS %lu SOURCE_MS 0 REJECT %s BAD %lu PARSE_BAD %lu PKP %ld PKI %ld PKD %ld TKP %ld TKI %ld TKD %ld\r\n",
        control.valid ? "tracking":"waiting",control.automatic ? "auto":"manual",
        control.valid,control.outputs,control.dx,control.dy,control.pan_us,control.tilt_us,
        control.pan_us,control.tilt_us,(unsigned long)control.frames,
        (unsigned long)control.received_ms,guardian.last_reject,
        (unsigned long)control.rejected,(unsigned long)guardian.rejected,
        (long)(control.pan_pid.Kp*100+0.5f),(long)(control.pan_pid.Ki*100+0.5f),
        (long)(control.pan_pid.Kd*100+0.5f),(long)(control.tilt_pid.Kp*100+0.5f),
        (long)(control.tilt_pid.Ki*100+0.5f),(long)(control.tilt_pid.Kd*100+0.5f));
    if(n<0 || n>=(int)sizeof(text) || !board_send(text)) ++tx_dropped;
    n=snprintf(text,sizeof(text),"S1STAT SAFE %s WHY %s NONCE %08lx%08lx SEQ %lu TX_DROP %lu FW 15\r\n",
        safety_state_name(&guardian),safety_reason_name(&guardian),
        (unsigned long)guardian.nonce_hi,(unsigned long)guardian.nonce_lo,
        (unsigned long)guardian.sequence,(unsigned long)tx_dropped);
    if(n<0 || n>=(int)sizeof(text) || !board_send(text)) ++tx_dropped;
}
static void console_expire(uint32_t now)
{
    if (used && (uint32_t)(now-command_last_ms)>=SAFETY_COMMAND_MS) {
        trip(SAFE_STALE); guardian.last_reject="partial_timeout"; dropping=1;
    }
}
static void console_feed(uint8_t byte, uint32_t received, uint32_t now)
{
    int accepted;
#ifdef S1ACK1
    ack_request_t request;
    const char *command;
#endif
    uint32_t prior_sequence;
    safe_state_t prior_state;
    console_expire(received);
    if ((uint32_t)(now-received)>=SAFETY_COMMAND_MS) {
        trip(SAFE_STALE); guardian.last_reject="queued_stale"; dropping=1;
    }
    command_last_ms=received;
    if (byte=='\r' || byte=='\n') {
        if (used || dropping) {
            line[used]=0;
            if (!dropping && !board_button()) {
                prior_state=guardian.state; prior_sequence=guardian.sequence;
                #ifdef S1ACK1
                command=ack_prepare(line,&request);
                if (!command) { used=dropping=0; return; }
                if (request.kind && board_tx_free()<256u) {
                    trip(SAFE_PARSE); guardian.last_reject="tx_full";
                    ++tx_dropped; used=dropping=0; return;
                }
                accepted=safety_command(&guardian,&control,command,received,now);
#else
                accepted=safety_command(&guardian,&control,line,received,now);
#endif
                if (accepted && (prior_state!=guardian.state ||
                    (prior_sequence!=guardian.sequence && guardian.mode_ms==received &&
                     strstr(line," hb*")==0))) flush_vision();
                if (!accepted) (void)board_send("ERROR guarded_command\r\n");
                if (!safety_armed(&guardian)) disarm_queues();
                else if (accepted && !board_guard_refresh(guardian.live_ms)) trip(SAFE_LINK_TIMEOUT);
#ifdef S1ACK1
                poll_safety(now);
                board_outputs(safety_armed(&guardian)&&control.outputs,control.pan_us,control.tilt_us);
                ack_reply(&request,accepted);
#endif
                status();
            } else if (board_button()) trip(SAFE_KEY);
            used=dropping=0;
        }
    } else if (dropping) {
        return;
    } else if (byte>=32 && byte<=126 && used<sizeof(line)-1) {
        /* Preserve exact protected-frame bytes for CRC validation. */
        line[used++]=(char)byte;
    } else {
        trip(SAFE_PARSE); guardian.last_reject="line_overflow_or_byte"; dropping=1;
    }
}
static void poll_safety(uint32_t now)
{
    safe_state_t before;
    unsigned event=board_guard_take_event();
    if (event) trip(event==BOARD_GUARD_KEY ? SAFE_KEY :
                    event==BOARD_GUARD_UART ? SAFE_UART :
                    event==BOARD_GUARD_RANGE ? SAFE_PARSE : SAFE_LINK_TIMEOUT);
    if (board_take_fault()) trip(SAFE_UART);
    if (board_button()) trip(SAFE_KEY);
    if (parser.used && (uint32_t)(now-parser.last_ms)>=BYTE_TIMEOUT_MS) trip(SAFE_VISION);
    before=guardian.state;
    safety_tick(&guardian,&control,now);
    if (before!=SAFE_FAULT && guardian.state==SAFE_FAULT) disarm_queues();
}
static void vision_byte(uint8_t byte, uint32_t received, uint32_t now)
{
    if (guardian.state==SAFE_AUTO) {
        uint32_t rejected=control.rejected;
        int complete=vision_feed(&parser,&control,byte,received,now);
        if (rejected!=control.rejected || (complete && !control.valid)) trip(SAFE_VISION);
    }
}
int main(void)
{
    uint32_t last_status=0, received, hi,lo;
    uint8_t byte; int entropy_ok;
    tracking_init(&control); vision_init(&parser); board_init();
    entropy_ok=board_session_nonce(&hi,&lo);
    safety_init(&guardian,hi,lo,entropy_ok);
    (void)board_send("SKYSTAR F407 v15 GUARDED_SESSION HSI16 PWM_OFF CONSOLE=" CONSOLE_LABEL "\r\n");
    for (;;) {
        unsigned count;
        uint32_t now=board_ms();
        poll_safety(now); console_expire(now);
        for (count=0;count<32 && board_pc_timed_byte(&byte,&received);++count)
            console_feed(byte,received,board_ms());
        for (count=0;count<64 && board_vision_byte(&byte,&received);++count)
            vision_byte(byte,received,board_ms());
        now=board_ms();
        poll_safety(now); tracking_tick(&control,now);
        board_outputs(safety_armed(&guardian) && control.outputs,control.pan_us,control.tilt_us);
        if ((uint32_t)(now-last_status)>=100u) { last_status=now; status(); }
        board_poll_tx();
    }
}
