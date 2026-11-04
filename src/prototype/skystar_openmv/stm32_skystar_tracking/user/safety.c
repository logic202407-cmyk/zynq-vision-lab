/* v15 guarded console. CRC is error detection, not authentication. */
#include "safety.h"
#include <string.h>

int safety_armed(const safety_t *s)
{ return s->state == SAFE_ARMED || s->state == SAFE_MANUAL || s->state == SAFE_AUTO; }
static void rotate(safety_t *s)
{
    if (++s->nonce_lo == 0 && ++s->nonce_hi == 0) s->entropy_ok = 0;
    s->sequence = 0;
}
void safety_init(safety_t *s, uint32_t hi, uint32_t lo, int entropy_ok)
{
    memset(s, 0, sizeof(*s));
    s->last_reject="none";
    s->nonce_hi = hi; s->nonce_lo = lo;
    s->entropy_ok = (uint8_t)(entropy_ok && (hi || lo));
    s->state = s->entropy_ok ? SAFE_STOPPED : SAFE_FAULT;
    s->reason = s->entropy_ok ? SAFE_BOOT : SAFE_ENTROPY;
}
void safety_trip(safety_t *s, tracking_t *c, safe_reason_t reason)
{
    tracking_stop(c);
    /* Preserve the first cause and challenge while already latched. */
    if (s->state != SAFE_FAULT) { rotate(s); s->reason = reason; }
    s->state = SAFE_FAULT;
}
static void stop(safety_t *s, tracking_t *c)
{
    tracking_stop(c);
    if (s->state == SAFE_FAULT) return; /* stop cannot erase a fault */
    if (s->state != SAFE_STOPPED) rotate(s);
    s->state = SAFE_STOPPED; s->reason = SAFE_STOP;
}
void safety_tick(safety_t *s, tracking_t *c, uint32_t now)
{
    if (!safety_armed(s)) return;
    if ((uint32_t)(now-s->live_ms) >= SAFETY_LEASE_MS)
        safety_trip(s,c,SAFE_LINK_TIMEOUT);
    else if (s->state == SAFE_AUTO &&
             (uint32_t)(now-(c->valid ? c->received_ms : s->mode_ms)) >= FRAME_TIMEOUT_MS)
        safety_trip(s,c,SAFE_VISION);
}
uint16_t safety_crc(const char *data, unsigned count)
{
    uint16_t crc=0xffffu; unsigned i;
    while (count--) {
        crc ^= (uint16_t)(uint8_t)*data++ << 8;
        for (i=0;i<8;++i) {
            if (crc&0x8000u) crc=(uint16_t)((crc<<1)^0x1021u);
            else crc=(uint16_t)(crc<<1);
        }
    }
    return crc;
}
static int hex(char ch)
{
    if (ch>='0' && ch<='9') return ch-'0';
    if (ch>='a' && ch<='f') return ch-'a'+10;
    if (ch>='A' && ch<='F') return ch-'A'+10;
    return -1;
}
static int hexword(const char *p, unsigned n, uint32_t *value)
{
    uint32_t v=0; unsigned i; int d;
    for (i=0;i<n;++i) { d=hex(p[i]); if(d<0) return 0; v=(v<<4)|(unsigned)d; }
    *value=v; return 1;
}
static int reject(safety_t *s, tracking_t *c, int trip, const char *why)
{
    ++s->rejected; s->last_reject=why;
    if (trip) safety_trip(s,c,SAFE_PARSE);
    return 0;
}
int safety_command(safety_t *s, tracking_t *c, const char *line, uint32_t rx, uint32_t now)
{
    const char *star, *p; char payload[32];
    uint32_t hi,lo,seq=0,wire_crc,digit; unsigned n,digits=0;
    safety_tick(s,c,now);
    if (!strcmp(line,"stop") || !strcmp(line,"STOP")) { stop(s,c); return 1; }
    if (!strcmp(line,"st") || !strcmp(line,"ST")) return 1;
    if ((uint32_t)(now-rx) >= SAFETY_COMMAND_MS) {
        ++s->rejected; s->last_reject="stale"; safety_trip(s,c,SAFE_STALE); return 0;
    }
    n=(unsigned)strlen(line);
    if (n<29 || n>=SAFETY_LINE_BYTES || strncmp(line,"s1 ",3))
        return reject(s,c,safety_armed(s),"unframed");
    star=strchr(line,'*');
    if (!star || strlen(star+1)!=4 || !hexword(star+1,4,&wire_crc) ||
        safety_crc(line,(unsigned)(star-line))!=(uint16_t)wire_crc)
        return reject(s,c,1,"crc");
    if (!hexword(line+3,8,&hi) || !hexword(line+11,8,&lo) || line[19]!=' ')
        return reject(s,c,1,"format");
    p=line+20;
    while (p<star && *p>='0' && *p<='9') {
        digit=(uint32_t)(*p++-'0');
        if (seq>(0xffffffffu-digit)/10u) return reject(s,c,1,"format");
        seq=seq*10u+digit; ++digits;
    }
    if (!digits || p>=star || *p++!=' ' || star-p<1 || star-p>31)
        return reject(s,c,1,"format");
    n=(unsigned)(star-p); memcpy(payload,p,n); payload[n]=0;
    /* Old session, duplicate and reordered frames cannot extend the lease. */
    if (hi!=s->nonce_hi || lo!=s->nonce_lo) return reject(s,c,0,"session");
    if (!strcmp(payload,"arm")) {
        if (!s->entropy_ok || seq!=0 || safety_armed(s)) return reject(s,c,0,"arm");
        tracking_stop(c); s->state=SAFE_ARMED; s->reason=SAFE_READY;
        s->sequence=0; s->live_ms=rx; s->mode_ms=rx; s->last_reject="none"; return 1;
    }
    if (!safety_armed(s) || !seq || seq<=s->sequence) return reject(s,c,0,"sequence");
    if (!strcmp(payload,"hb")) { s->sequence=seq; s->live_ms=rx; s->last_reject="none"; return 1; }
    if (strcmp(payload,"home") && strcmp(payload,"auto") &&
        strncmp(payload,"pan ",4) && strncmp(payload,"tlt ",4))
        return reject(s,c,1,"format");
    if (!tracking_command(c,payload)) return reject(s,c,1,"format");
    s->state=!strcmp(payload,"auto") ? SAFE_AUTO : SAFE_MANUAL;
    s->reason=SAFE_READY; s->sequence=seq; s->live_ms=rx; s->mode_ms=rx; s->last_reject="none";
    return 1;
}
const char *safety_state_name(const safety_t *s)
{
    static const char *names[]={"stopped","armed","manual","auto","fault"};
    return names[s->state];
}
const char *safety_reason_name(const safety_t *s)
{
    static const char *names[]={"boot","stop","ready","link_timeout","stale",
                               "parse","uart","key","vision","entropy"};
    return names[s->reason];
}
