/* Optional S1ACK1 response extension. Included only by main.c. */
typedef struct {
    unsigned kind; /* 0 legacy, 1 query, 2 protected command */
    char id[33], seq[11], crc[5], op[8];
} ack_request_t;
static int ack_hex(const char *s, unsigned n) {
    unsigned i;
    for(i=0;i<n;i++) if (!((s[i]>='0'&&s[i]<='9')||(s[i]>='a'&&s[i]<='f')||(s[i]>='A'&&s[i]<='F'))) return 0;
    return 1;
}
static void ack_lower(char *s) {
    for(;*s;s++) if(*s>='A'&&*s<='F') *s=(char)(*s+('a'-'A'));
}
static unsigned ack_hexval(const char *s, unsigned n) {
    unsigned v=0,i; for(i=0;i<n;i++) v=(v<<4)|(s[i]<='9'?s[i]-'0':s[i]<='F'?s[i]-'A'+10:s[i]-'a'+10); return v;
}
static const char *ack_prepare(const char *s, ack_request_t *r) {
    const char *star=strchr(s,'*'), *p, *end; unsigned n,i; uint32_t seq=0,d;
    memset(r,0,sizeof(*r));
    if(strncmp(s,"s1q ",4) && strncmp(s,"s1 ",3)) return s;
    if(!star || strlen(star+1)!=4 || !ack_hex(star+1,4) ||
       safety_crc(s,(unsigned)(star-s))!=ack_hexval(star+1,4)) {
        trip(SAFE_PARSE); guardian.last_reject="crc"; return 0;
    }
    memcpy(r->crc,star+1,4);ack_lower(r->crc);
    if(!strncmp(s,"s1q ",4)) {
        if(star-s<39 || !ack_hex(s+4,32) || s[36]!=' ') goto bad;
        p=s+37;n=(unsigned)(star-p);
        if(!((n==2&&!memcmp(p,"st",2))||(n==4&&!memcmp(p,"stop",4)))) goto bad;
        memcpy(r->id,s+4,32);ack_lower(r->id);memcpy(r->op,p,n);r->kind=1;
        return n==2?"st":"stop";
    }
    if(star-s<24 || !ack_hex(s+3,16) || s[19]!=' ') goto bad;
    memcpy(r->id,s+3,16);ack_lower(r->id);p=s+20;end=p;
    while(end<star && *end>='0'&&*end<='9') {
        d=(uint32_t)(*end-'0');if(seq>(0xffffffffu-d)/10u) goto bad;
        seq=seq*10u+d;end++;
    }
    n=(unsigned)(end-p);if(!n||end>=star||*end!=' ') goto bad;
    (void)snprintf(r->seq,sizeof(r->seq),"%lu",(unsigned long)seq);p=end+1;end=p;
    while(end<star && *end!=' ') end++;
    n=(unsigned)(end-p);if(!n||n>=sizeof(r->op)) goto bad;
    for(i=0;i<n;i++) if(p[i]<'a'||p[i]>'z') goto bad;
    memcpy(r->op,p,n);r->kind=2;return s;
bad:
    trip(SAFE_PARSE);guardian.last_reject="format";return 0;
}
static void ack_reply(const ack_request_t *r, int accepted) {
    char text[256];int n,m;unsigned mask,pan,tilt;
    const char *result=accepted?"ACCEPT":"REJECT";
    if(!r->kind) return;
    board_pwm_snapshot(&mask,&pan,&tilt);
    if(accepted && r->kind==2 &&
       (!safety_armed(&guardian) || (control.outputs && mask!=3u))) result="ABORTED";
    if(r->kind==1 && !strcmp(r->op,"st")) {
        n=snprintf(text,sizeof(text),"S1SYNC %s S1ACK1 %08lx%08lx %s %s %u %u %u %lu %lu",
            r->id,(unsigned long)guardian.nonce_hi,(unsigned long)guardian.nonce_lo,
            safety_state_name(&guardian),safety_reason_name(&guardian),
            control.pan_us,control.tilt_us,mask,(unsigned long)guardian.sequence,(unsigned long)tx_dropped);
    } else {
        n=snprintf(text,sizeof(text),"S1ACK %s %s %s %s %s %s %s %08lx%08lx %s %s %s %u %u %u %u %u",
            r->kind==1?"Q":"S",r->id,r->kind==1?"-":r->seq,r->kind==1?"-":r->crc,r->op,
            result,accepted&&!strcmp(result,"ACCEPT")?"REG":"NONE",
            (unsigned long)guardian.nonce_hi,(unsigned long)guardian.nonce_lo,
            safety_state_name(&guardian),safety_reason_name(&guardian),
            accepted?"none":guardian.last_reject,control.pan_us,control.tilt_us,mask,pan,tilt);
    }
    if(n<0 || n>249) { trip(SAFE_PARSE);++tx_dropped;return; }
    m=snprintf(text+n,sizeof(text)-(unsigned)n,"*%04x\n",safety_crc(text,(unsigned)n));
    if(m!=6 || !board_send(text)) { trip(SAFE_PARSE);++tx_dropped; }
}
