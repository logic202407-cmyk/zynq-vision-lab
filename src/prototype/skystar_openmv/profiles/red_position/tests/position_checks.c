#include "tracking.h"
#include "safety.h"
#include <stdio.h>
#include <math.h>
#define TRACK_AIM_DX_PX 0.0f
#define TRACK_AIM_DY_PX 0.0f
#define MAX_TRACK_JUMP_PX 40.0f
#define FILTER_ALPHA_PAN 0.35f
#define FILTER_ALPHA_TILT 0.20f
#define DEADBAND_PX 3
#define MAX_PULSE_STEP_US 60
#define MAX_PULSE_STEP_US_MAX 350
#define PAN_SAFE_MIN ((int32_t)PAN_MIN_US)
#define PAN_SAFE_MAX ((int32_t)PAN_MAX_US)
#define TILT_SAFE_MIN ((int32_t)TILT_MIN_US)
#define TILT_SAFE_MAX ((int32_t)TILT_MAX_US)
#define __get_PRIMASK() 0
#define __disable_irq() ((void)0)
#define __set_PRIMASK(x) ((void)(x))
#define usart3_stopped() 0
#define usart3_manual_active() 0
#define usart3_manual_seq() 0
#define servo_set_pan_us(x) ((void)(x))
#define servo_set_tilt_us(x) ((void)(x))
static void reference(tracking_t *c,int16_t dx,int16_t dy,float dt){
 struct {int16_t dx,dy;} target={dx,dy}; struct {int faults;} g_parser={0};
 int command_seen=0,faults_seen=0;unsigned mask=0;
 float clamp_dx,clamp_dy;int16_t abs_dx,abs_dy;int filt_init=!c->filter_ready;
#define last_raw_dx c->raw_dx
#define last_raw_dy c->raw_dy
#define filt_dx c->filt_dx
#define filt_dy c->filt_dy
#define pid_pan c->pan_pid
#define pid_tilt c->tilt_pid
#define pan_pulse c->pan_us
#define tilt_pulse c->tilt_us
                {
                    if (filt_init) {
                        /* 重新锁定后的第一帧: 直接用当前位置作基准, 不限速。
                         * 若这里也限速, 会凭空制造一个从 0 到真实位置的跳变,
                         * 反而拖慢恢复。跳变保护只用于之后的帧间比较。 */
                        clamp_dx = (float)target.dx - TRACK_AIM_DX_PX;
                        clamp_dy = (float)target.dy - TRACK_AIM_DY_PX;
                    } else {
                        float rd = (float)target.dx - TRACK_AIM_DX_PX - last_raw_dx;
                        float ry = (float)target.dy - TRACK_AIM_DY_PX - last_raw_dy;
                        if (rd >  MAX_TRACK_JUMP_PX) rd =  MAX_TRACK_JUMP_PX;
                        if (rd < -MAX_TRACK_JUMP_PX) rd = -MAX_TRACK_JUMP_PX;
                        if (ry >  MAX_TRACK_JUMP_PX) ry =  MAX_TRACK_JUMP_PX;
                        if (ry < -MAX_TRACK_JUMP_PX) ry = -MAX_TRACK_JUMP_PX;
                        clamp_dx = last_raw_dx + rd;
                        clamp_dy = last_raw_dy + ry;
                    }
                    last_raw_dx = clamp_dx;
                    last_raw_dy = clamp_dy;
                }

                /*
                 * (2) 一阶低通滤波 (对 dx/dy, 不对脉宽)。
                 * 目的: 色块中心本身有 ±18px 量级的抖动, 直接送进 PID
                 * 会被 Kp 放大成脉宽抖动, 再经云台转动反馈回画面, 形成自激。
                 * 两轴系数不同, 原因见 FILTER_ALPHA_PAN/TILT 的定义。
                 */
                if (filt_init) {
                    filt_dx = clamp_dx;
                    filt_dy = clamp_dy;
                    filt_init = 0;
                } else {
                    filt_dx += FILTER_ALPHA_PAN  * (clamp_dx - filt_dx);
                    filt_dy += FILTER_ALPHA_TILT * (clamp_dy - filt_dy);
                }

                /* 死区判断改用滤波后的值, 避免噪声在死区边界反复触发 */
                abs_dx = (filt_dx >= 0.0f) ? (int16_t)(filt_dx + 0.5f) : (int16_t)(-filt_dx + 0.5f);
                abs_dy = (filt_dy >= 0.0f) ? (int16_t)(filt_dy + 0.5f) : (int16_t)(-filt_dy + 0.5f);

                if (abs_dx > DEADBAND_PX || abs_dy > DEADBAND_PX) {
                    /* 本次 H7 Plus 安装方向：两轴反馈均取反；俯仰经上板纠正。 */
                    float corr_pan  = pid_update(&pid_pan,  0.0f, -filt_dx, dt);
                    float corr_tilt = pid_update(&pid_tilt, 0.0f, -filt_dy, dt);

                    /* 修正量叠加到中点, 转为绝对脉宽 */
                    int32_t pan  = (int32_t)PAN_HOME_US + (int32_t)corr_pan;
                    int32_t tilt = (int32_t)TILT_HOME_US + (int32_t)corr_tilt;

                    /*
                     * 输出限速: 按"时间"限速而不是按"帧"限速。
                     * 原来固定 MAX_PULSE_STEP_US/帧, 帧率一变实际角速度就跟着变
                     * (10fps 时只有 600us/s, 而 100fps 时能到 6000us/s)。
                     * 现在按 dt 折算: 每 10ms 允许走 MAX_PULSE_STEP_US,
                     * 于是帧率越低、单帧步长自动放得越大, 速度上限保持恒定。
                     */
                    int32_t step = (int32_t)(MAX_PULSE_STEP_US * (dt / 0.01f) + 0.5f);
                    if (step < MAX_PULSE_STEP_US)             step = MAX_PULSE_STEP_US;
                    if (step > MAX_PULSE_STEP_US_MAX)         step = MAX_PULSE_STEP_US_MAX;

                    if (pan  > (int32_t)pan_pulse  + step) pan  = (int32_t)pan_pulse  + step;
                    if (pan  < (int32_t)pan_pulse  - step) pan  = (int32_t)pan_pulse  - step;
                    if (tilt > (int32_t)tilt_pulse + step) tilt = (int32_t)tilt_pulse + step;
                    if (tilt < (int32_t)tilt_pulse - step) tilt = (int32_t)tilt_pulse - step;

                    /* 裁剪到各自安全范围 */
                    if (pan  < PAN_SAFE_MIN) pan  = PAN_SAFE_MIN;
                    if (pan  > PAN_SAFE_MAX) pan  = PAN_SAFE_MAX;
                    if (tilt < TILT_SAFE_MIN) tilt = TILT_SAFE_MIN;
                    if (tilt > TILT_SAFE_MAX) tilt = TILT_SAFE_MAX;

                    mask = __get_PRIMASK();
                    __disable_irq();
                    if (!usart3_stopped() && !usart3_manual_active() &&
                        command_seen == usart3_manual_seq() && faults_seen == g_parser.faults) {
                        pan_pulse = (uint16_t)pan;
                        tilt_pulse = (uint16_t)tilt;
                        servo_set_pan_us(pan_pulse);
                        servo_set_tilt_us(tilt_pulse);
                    }
                    __set_PRIMASK(mask);
                }

 c->filter_ready=!filt_init;
#undef last_raw_dx
#undef last_raw_dy
#undef filt_dx
#undef filt_dy
#undef pid_pan
#undef pid_tilt
#undef pan_pulse
#undef tilt_pulse
}
static int failed;
#define CHECK(x,m) do{printf("%s %s\n",(x)?"PASS":"FAIL",m);if(!(x))failed++;}while(0)
int main(void){tracking_t c,r;safety_t g;unsigned t=10,i;int mismatch=0;
 tracking_init(&c);tracking_init(&r);tracking_auto(&c);
 tracking_observe(&c,20,-7,1,t,t);t+=20;tracking_observe(&c,20,-7,1,t,t);t+=20;
 for(i=0;i<1500;i++,t+=20){int16_t dx=(int16_t)((i*7)%160-80),dy=(int16_t)((i*3)%120-59);
 tracking_observe(&c,dx,dy,1,t,t);reference(&r,dx,dy,i?0.02f:0.01f);
 if(c.pan_us!=r.pan_us||c.tilt_us!=r.tilt_us||fabsf(c.pan_pid.integral-r.pan_pid.integral)>0.001f||fabsf(c.tilt_pid.integral-r.tilt_pid.integral)>0.001f)mismatch++;
 }
 CHECK(!mismatch,"1500 frames match extracted teammate control block with documented bench constants");
 CHECK(c.pan_us>=1300&&c.pan_us<=1700&&c.tilt_us>=1300&&c.tilt_us<=1700,"bench pulse bounds retained");
 safety_init(&g,1,2,1);g.state=SAFE_AUTO;g.mode_ms=t;g.live_ms=t;
 tracking_observe(&c,0,0,0,t,t);CHECK(!c.outputs&&c.automatic,"target loss pauses PWM but retains AUTO");
 g.live_ms=t+500;safety_tick(&g,&c,t+500);CHECK(g.state==SAFE_AUTO&&!c.outputs,"long visual absence stays paused while link lease is fresh");
 tracking_observe(&c,10,5,1,t+520,t+520);tracking_observe(&c,10,5,1,t+540,t+540);CHECK(!c.outputs,"two frames cannot reacquire");
 tracking_observe(&c,10,5,1,t+560,t+560);CHECK(c.outputs&&c.automatic,"third frame reacquires after long loss without blind fault reset");
 g.live_ms=t+560;safety_tick(&g,&c,t+1060);CHECK(g.state==SAFE_FAULT&&!c.outputs&&!c.automatic,"expired link lease still latches stop");
 tracking_observe(&c,10,5,1,t+1080,t+1080);CHECK(!c.outputs,"vision cannot restart faulted controller");
 tracking_auto(&c);tracking_stop(&c);tracking_observe(&c,10,5,1,t+1100,t+1100);CHECK(!c.outputs&&!c.automatic,"explicit STOP prevents automatic restart");
 printf("failures=%d\n",failed);return failed?1:0;}
