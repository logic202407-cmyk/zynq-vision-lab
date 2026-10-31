/* Included after actual board.c/main.c: exercises production entry points.
 * Deterministic register model only; no physical entropy/timing claims. */
static void safe_fixture(void)
{
    model_pll=model_rng=model_rng_reads=0;
    R(RCC)=3; R(RCC+8)=0; R(GPIOA+0x10)=0; board_init();
    tracking_init(&control); vision_init(&parser);
    safety_init(&guardian,0x12345678u,0x87654321u,1);
    used=dropping=0; command_last_ms=0; tx_dropped=0;
}
static void make_frame(char *out, const char *payload, uint32_t seq)
{
    unsigned n=(unsigned)sprintf(out,"s1 %08lx%08lx %lu %s",
        (unsigned long)guardian.nonce_hi,(unsigned long)guardian.nonce_lo,
        (unsigned long)seq,payload);
    sprintf(out+n,"*%04x\n",safety_crc(out,n));
}
static void safe_send(const char *payload, uint32_t seq, uint32_t rx, uint32_t now)
{
    char frame[96]; make_frame(frame,payload,seq);
    milliseconds=now; command_text(frame,rx,now);
}
static void safe_start(void)
{
    safe_fixture(); safe_send("arm",0,0,0);
    CHECK(guardian.state==SAFE_ARMED && !control.outputs && R(TIM4+0x20)==0);
    safe_send("pan 1550",1,10,10);
    board_outputs(control.outputs,control.pan_us,control.tilt_us);
    CHECK(control.pan_us==1550 && guardian.state==SAFE_MANUAL && R(TIM4+0x20)==17);
}
static void safe_vision(int dx, int dy, unsigned valid, uint32_t now)
{
    uint8_t b[8]={0xaa,0xff,(uint8_t)dx,(uint8_t)(dx>>8),
        (uint8_t)dy,(uint8_t)(dy>>8),(uint8_t)valid,0xee}; unsigned i;
    milliseconds=now;
    for(i=0;i<8;++i) vision_byte(b[i],now,now);
}
static void safety_checks(void)
{
    char old[96],bad[96]; uint32_t hi,lo; unsigned i;
    CHECK(safety_crc("123456789",9)==0x29b1u);
    safe_fixture(); board_outputs(1,1500,1500);
    CHECK(!pwm_enabled && R(TIM4+0x20)==0 && !control.outputs);
    command_text("home\n",0,0); CHECK(!control.outputs && !guard_active);
    safe_send("home",1,0,0); CHECK(!control.outputs && guardian.state==SAFE_STOPPED);
    command_text("s1 1234567887654321 0 arm*be15\n",0,0); /* Python CRC fixture */
    CHECK(guardian.state==SAFE_ARMED && !control.outputs);
    safe_start(); make_frame(old,"pan 1550",1);
    command_text(old,100,100); CHECK(guardian.live_ms==10 && guardian.sequence==1);
    command_text("st\n",400,400); CHECK(guardian.live_ms==10 && guardian.state==SAFE_MANUAL);
    safe_send("arm",0,450,450); CHECK(guardian.live_ms==10 && guardian.state==SAFE_MANUAL);
    milliseconds=509; board_outputs(1,1550,1500); CHECK(pwm_enabled);
    SysTick_Handler(); /* No foreground polling: ISR must stop at 500ms. */
    CHECK(!pwm_enabled && R(TIM4+0x20)==0 && !guard_active);
    CHECK(!board_guard_refresh(510));
    poll_safety(510); CHECK(guardian.state==SAFE_FAULT && guardian.reason==SAFE_LINK_TIMEOUT);
    CHECK(!control.outputs && !control.automatic);
    command_text(old,511,511); CHECK(guardian.state==SAFE_FAULT && !control.outputs);
    safe_send("hb",2,512,512); CHECK(guardian.state==SAFE_FAULT && !control.outputs);
    command_text("stop\nst\n",513,513);
    CHECK(guardian.state==SAFE_FAULT && guardian.reason==SAFE_LINK_TIMEOUT);
    safe_vision(50,50,1,514); CHECK(!control.outputs && !control.valid);
    /* A genuinely new operator arm only grants a lease, never enables PWM. */
    safe_send("arm",0,520,520); CHECK(guardian.state==SAFE_ARMED && !control.outputs);
    safe_send("tlt 1550",1,521,521); CHECK(control.outputs && control.tilt_us==1550);
    safe_send("hb",2,900,900); CHECK(guardian.live_ms==900);
    safe_send("hb",2,1000,1000); CHECK(guardian.live_ms==900); /* duplicate */
    safe_send("home",1,1001,1001); CHECK(guardian.live_ms==900 && control.tilt_us==1550);
    poll_safety(1399); CHECK(guardian.state==SAFE_MANUAL);
    poll_safety(1400); CHECK(guardian.state==SAFE_FAULT && !control.outputs);

    safe_start(); make_frame(bad,"home",2); bad[5]=bad[5]=='0' ? '1':'0';
    command_text(bad,20,20); CHECK(guardian.state==SAFE_FAULT && !control.outputs);
    CHECK(!strcmp(guardian.last_reject,"crc"));
    safe_start(); make_frame(old,"home",2); command_text("stop\n",20,20);
    CHECK(guardian.state==SAFE_STOPPED && !control.outputs);
    command_text(old,21,21); CHECK(guardian.state==SAFE_STOPPED && !control.outputs);
    safe_start(); safe_send("pan 1550",2,20,20);
    CHECK(control.pan_us==1550 && control.tilt_us==1500 && guardian.live_ms==20);
    safe_start(); make_frame(bad,"hb",0xffffffffu); command_text(bad,20,20);
    CHECK(guardian.sequence==0xffffffffu);
    safe_send("hb",1,21,21); CHECK(guardian.sequence==0xffffffffu && guardian.live_ms==20);
    safe_start(); safe_send("home",2,20,220);
    CHECK(guardian.state==SAFE_FAULT && guardian.reason==SAFE_STALE && !control.outputs);
    safe_start(); command_text("s1 123",20,20); console_expire(219); CHECK(control.outputs);
    console_expire(220); CHECK(!control.outputs && guardian.state==SAFE_FAULT);
    command_text("4567887654321 2 home*0000\n",221,221); CHECK(!control.outputs);
    /* Fault queries/arming must still work across normal 32-byte loop slices. */
    make_frame(bad,"arm",0); command_text("\n",222,222);
    milliseconds=223;
    for(i=0;bad[i];++i) {
        console_feed((uint8_t)bad[i],223,223);
        if(i==20) poll_safety(223);
    }
    CHECK(guardian.state==SAFE_ARMED && !control.outputs);
    safe_send("home",1,224,224); CHECK(control.outputs);

    safe_start(); R(CONSOLE)=8; R(CONSOLE+4)=0;
#if CONSOLE_USART == 3
    USART3_IRQHandler();
#else
    USART1_IRQHandler();
#endif
    CHECK(!pwm_enabled && R(TIM4+0x20)==0);
    board_outputs(1,1550,1500); CHECK(!pwm_enabled);
    poll_safety(11); CHECK(guardian.state==SAFE_FAULT && guardian.reason==SAFE_UART);
    safe_start();
    for(i=0;i<256;++i) { R(CONSOLE)=32; R(CONSOLE+4)='x';
#if CONSOLE_USART == 3
        USART3_IRQHandler();
#else
        USART1_IRQHandler();
#endif
    }
    CHECK(!pwm_enabled && R(TIM4+0x20)==0);
    poll_safety(11); CHECK(guardian.state==SAFE_FAULT && guardian.reason==SAFE_UART);
    CHECK(pc.tail==pc.head && vision.tail==vision.head);
    safe_start(); R(GPIOA+0x10)=1; SysTick_Handler();
    CHECK(!pwm_enabled); poll_safety(11);
    CHECK(guardian.reason==SAFE_KEY && guardian.state==SAFE_FAULT);
    R(GPIOA+0x10)=0; safe_vision(20,20,1,12); CHECK(!control.outputs);
    safe_start(); board_outputs(1,1701,1500); CHECK(!pwm_enabled && !guard_active);
    poll_safety(11); CHECK(guardian.state==SAFE_FAULT && guardian.reason==SAFE_PARSE);

    safe_fixture(); safe_send("arm",0,0,0); safe_send("auto",1,1,1);
    safe_vision(20,10,1,10); CHECK(control.outputs && guardian.state==SAFE_AUTO);
    poll_safety(209); CHECK(control.outputs);
    poll_safety(210); CHECK(!control.outputs && guardian.reason==SAFE_VISION);
    safe_vision(20,10,1,211); CHECK(!control.outputs && guardian.state==SAFE_FAULT);
    safe_fixture(); safe_send("arm",0,0,0); safe_send("auto",1,1,1);
    safe_vision(0,0,0,10); CHECK(guardian.state==SAFE_FAULT && !control.outputs);
    safe_fixture(); safe_send("arm",0,0,0); safe_send("auto",1,1,1);
    vision_byte(0xaa,2,2); poll_safety(22);
    CHECK(guardian.state==SAFE_FAULT && !control.outputs);

    safe_fixture(); safe_send("arm",0,0xfffffff0u,0xfffffff0u);
    safe_send("home",1,0xfffffff0u,0xfffffff0u);
    poll_safety(0x1e3u); CHECK(control.outputs);
    poll_safety(0x1e4u); CHECK(!control.outputs && guardian.state==SAFE_FAULT);
    /* New boot entropy rejects all frames from a preceding boot. */
    safe_fixture(); make_frame(old,"arm",0);
    safety_init(&guardian,0xabcdef01u,0x11111111u,1);
    command_text(old,0,0); CHECK(guardian.state==SAFE_STOPPED && !control.outputs);
    safety_init(&guardian,0,0,0); safe_send("arm",0,1,1);
    CHECK(guardian.state==SAFE_FAULT && guardian.reason==SAFE_ENTROPY && !control.outputs);

    /* Actual RNG register code: bounded errors, no fixed-seed fallback. */
    safe_fixture(); model_pll=1; model_rng=1;
    CHECK(board_session_nonce(&hi,&lo) && hi && lo && hi!=lo);
    CHECK((R(RCC+8)&12u)==0 && R(CONSOLE+8)==139 && R(TIM4+0x28)==15);
    CHECK(R(RCC+4)==(16u|(192u<<6)|(4u<<24)));
    for(i=2;i<=5;++i) {
        model_rng=i; CHECK(!board_session_nonce(&hi,&lo) && !hi && !lo);
        CHECK(R(TIM4+0x20)==0);
    }
    model_rng=1; model_pll=2; CHECK(!board_session_nonce(&hi,&lo));
    model_pll=3; CHECK(!board_session_nonce(&hi,&lo)); model_pll=model_rng=0;

    /* Deterministic malformed-input regression; every case starts enabled. */
    for(i=0;i<1000;++i) {
        unsigned j; uint32_t random=0x92ac31u+i; safe_start();
        make_frame(bad,"home",2);
        bad[3+(i%16)] = '!'; /* invalidates CRC and/or nonce format */
        command_text(bad,20,20); CHECK(guardian.state==SAFE_FAULT && !control.outputs);
        for(j=0;j<32;++j) {
            random=random*1664525u+1013904223u;
            console_feed((uint8_t)(random>>24),21,21);
            poll_safety(21); board_outputs(control.outputs,control.pan_us,control.tilt_us);
            CHECK(!control.outputs && R(TIM4+0x20)==0);
        }
    }
    safe_fixture(); tx_head=tx_tail=0; status(); tx[tx_head]=0;
    CHECK(tx_head<511 && strstr(tx,"SAFE stopped WHY boot")!=0);
}
