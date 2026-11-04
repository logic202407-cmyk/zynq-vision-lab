#include "board.h"
#include "tracking.h"
#include "tracking_profile.h"
#ifdef SKYSTAR_TEAM_PROFILE
#include "laser_lock.h"
static laser_lock_t port_laser;
#endif
#include "safety.h"
#include <stdio.h>
#include <string.h>

#if defined(C1_CLOSED_LOOP) && (!defined(C1_OBSERVATIONS) || !defined(S1ACK1))
#error C1_CLOSED_LOOP_requires_C1_OBSERVATIONS_and_S1ACK1
#endif

#ifdef C1_OBSERVATIONS
#include "gimbal_registry.h"
#include "vision_measurement.h"
static gimbal_registry_t observation_devices;
static measurement_store_t observations;
static uint32_t observation_nonce_hi,observation_nonce_lo;
static int c1_hex(char c){if(c>='0'&&c<='9')return c-'0';if(c>='a'&&c<='f')return c-'a'+10;return -1;}
static int c1_line(const char *s,uint32_t rx,uint32_t now);
#endif
static tracking_t control;
static vision_parser_t parser;
static safety_t guardian;
#ifdef C1_OBSERVATIONS
static void c1_expire(uint32_t now){
 measurement_slot_t *slot=&observations.camera[0];
 if(slot->session_bound&&(observation_nonce_hi!=guardian.nonce_hi||observation_nonce_lo!=guardian.nonce_lo))memset(&observations,0,sizeof(observations));
 measurement_tick(&observations,now);
}
static int c1_line(const char *s,uint32_t rx,uint32_t now){
 uint8_t packet[M2_BYTES];unsigned i;int a,b;uint32_t words[4]={0,0,0,0};
 uint16_t crc=0;char response[48];measurement_slot_t *slot=&observations.camera[0];
 c1_expire(now);
 if(!strncmp(s,"v2b ",4)){
  if(strlen(s)!=42||s[20]!=' '||s[37]!='*'||guardian.state!=SAFE_STOPPED||control.outputs||
     (uint32_t)(now-rx)>=SAFETY_COMMAND_MS)return 1;
  for(i=0;i<32;i++){a=c1_hex(s[4+i+(i>=16)]);if(a<0)return 1;words[i/8]=(words[i/8]<<4)|(unsigned)a;}
  for(i=38;i<42;i++){a=c1_hex(s[i]);if(a<0)return 1;crc=(uint16_t)((crc<<4)|a);}
  if(crc!=safety_crc(s,37)||!guardian.entropy_ok||words[0]!=guardian.nonce_hi||words[1]!=guardian.nonce_lo||(!words[2]&&!words[3]))return 1;
  if(slot->session_bound&&(words[2]<slot->session_hi||(words[2]==slot->session_hi&&words[3]<slot->session_lo)))return 1;
  memcpy(response,s,37);memcpy(response,"V2A ",4);
  (void)snprintf(response+37,sizeof(response)-37,"*%04x\n",safety_crc(response,37));
  if(!board_send(response))return 1; /* No ACK capacity: do not install session. */
  if(!slot->session_bound||words[2]!=slot->session_hi||words[3]!=slot->session_lo)
   (void)measurement_bind(&observations,0,words[2],words[3]);
  observation_nonce_hi=guardian.nonce_hi;observation_nonce_lo=guardian.nonce_lo;
  return 1; /* Duplicate binding is idempotent; never rewind frame sequence. */
 }
 if(strncmp(s,"v2 ",3))return 0;
 if(strlen(s)!=111)return 1;
 for(i=0;i<M2_BYTES;i++){a=c1_hex(s[3+i*2]);b=c1_hex(s[4+i*2]);if(a<0||b<0)return 1;packet[i]=(uint8_t)(a*16+b);}
 (void)measurement_receive(&observations,packet,M2_BYTES,rx,now);return 1;
}
#endif
#ifdef C1_OBSERVATIONS
static char line[128];
#else
static char line[SAFETY_LINE_BYTES];
#endif
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
#else
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
#endif
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
                #ifdef C1_OBSERVATIONS
                if(c1_line(line,received,now)){used=dropping=0;return;}
#endif
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
                else if (accepted && !board_guard_refresh(guardian.live_ms)) {
                    /* An ISR may already have latched UART/KEY before refresh.
                     * Consume that cause before considering a lease fallback. */
                    poll_safety(board_ms());
                    if (safety_armed(&guardian)) trip(SAFE_LINK_TIMEOUT);
                }
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
#if defined(C1_CLOSED_LOOP) && defined(C1_OBSERVATIONS)
#include "c1_feedback.h"
#endif
static void vision_byte(uint8_t byte, uint32_t received, uint32_t now)
{
#ifdef C1_OBSERVATIONS
    int observed=gimbal_openmv_byte(&observation_devices,0,byte,received,now);
#ifdef C1_CLOSED_LOOP
    if(observed)c1_feedback(now);
#else
    (void)observed;
#endif
#endif
    if (guardian.state==SAFE_AUTO) {
        uint32_t rejected=control.rejected;
        int complete=vision_feed(&parser,&control,byte,received,now);
        if (rejected!=control.rejected) trip(SAFE_VISION);
        /* Validity loss disables output in tracking; safety_tick bounds loss to 200ms. */
#ifdef SKYSTAR_TEAM_PROFILE
        if (complete) laser_lock_frame(&port_laser,received,
            (uint8_t)(control.valid && guardian.state==SAFE_AUTO));
#endif
    }
}
int main(void)
{
    uint32_t last_status=0, received, hi,lo;
    uint8_t byte; int entropy_ok;
    #ifdef C1_OBSERVATIONS
    gimbal_registry_init(&observation_devices);
    memset(&observations,0,sizeof(observations)); /* Explicit bind required; no boot session guess. */
#endif
    tracking_init(&control); vision_init(&parser); board_init();
#ifdef SKYSTAR_TEAM_PROFILE
    laser_lock_reset(&port_laser);
#endif
    entropy_ok=board_session_nonce(&hi,&lo);
    safety_init(&guardian,hi,lo,entropy_ok);
    (void)board_send("SKYSTAR F407 v15 GUARDED_SESSION HSI16 PWM_OFF CONSOLE=" CONSOLE_LABEL TRACK_PROFILE_LABEL "\r\n");
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
#ifdef SKYSTAR_TEAM_PROFILE
        board_laser_set(0); /* Camera-only calibration; no emitter output. */
#endif
        if ((uint32_t)(now-last_status)>=100u) { last_status=now; status(); }
        #ifdef C1_OBSERVATIONS
        c1_expire(now);gimbal_registry_tick(&observation_devices,now);
        (void)gimbal_record_targets(&observation_devices,0,control.pan_us,control.tilt_us);
        observation_devices.devices[0].safety_snapshot=guardian;
        observation_devices.devices[0].pwm_enabled=(uint8_t)(safety_armed(&guardian)&&control.outputs);
        observation_devices.devices[0].pwm_known=1;
        observation_devices.devices[0].fault=guardian.state==SAFE_FAULT?(uint8_t)guardian.reason:0;
        observation_devices.devices[0].owner=guardian.state==SAFE_AUTO?2:(safety_armed(&guardian)?1:0);
#endif
        board_poll_tx();
    }
}
