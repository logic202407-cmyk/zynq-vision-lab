/* Optional observation-only feedback. Included after guardian/observations.
 * No actuator, laser, authorization or lease operation is permitted here. */
#ifndef C1_FEEDBACK_H
#define C1_FEEDBACK_H
static uint32_t feedback_last_ms;
static void c1_feedback(uint32_t now)
{
    const tracking_t *v=&observation_devices.devices[0].control;
    measurement_slot_t *p=&observations.camera[0];
    char text[64];int n;unsigned valid;
    c1_expire(now);
    if (!p->session_bound) return;
    valid=v->valid && (uint32_t)(now-v->received_ms)<FRAME_TIMEOUT_MS &&
          p->fresh && (p->value.flags&3u)==3u;
    /* Limit valid observations to 20 Hz, and reserve capacity for control ACKs.
     * Invalid complete observations bypass rate limiting; full TX fails closed
     * at the FPGA's independent observation deadline. */
    if (valid && (uint32_t)(now-feedback_last_ms)<50u) return;
    if (board_tx_free()<320u) return;
    n=snprintf(text,sizeof(text),"F1 %08lx%08lx %08lx %08lx %04x %04x %x",
        (unsigned long)p->session_hi,(unsigned long)p->session_lo,
        (unsigned long)v->frames,(unsigned long)p->value.sequence,
        (unsigned)(uint16_t)v->dx,(unsigned)(uint16_t)v->dy,valid);
    if(n!=49)return;
    (void)snprintf(text+49,sizeof(text)-49,"*%04x\n",safety_crc(text,49));
    if(board_send(text))feedback_last_ms=now;
}
#endif
