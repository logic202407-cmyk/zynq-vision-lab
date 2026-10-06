/**
 * @file    main.c
 * @brief   二维云台追踪 — 主循环
 * @note    STM32F103C8T6 + 标准外设库 V3.5.0 + Keil5
 *
 * 阶段1: 串口解析 OpenMV 8字节帧 → 提取 dx/dy/flag
 * 阶段2: 舵机 PWM 驱动 — TIM2 CH1(PA0) Pan + CH2(PA1) Tilt
 * 阶段3: 双轴 PID 控制 — 实时追踪目标
 * 阶段4: OLED 显示 — I2C1 重映射 PB8(SCL)/PB9(SDA)
 *
 * 接线: OpenMV P4(TX) → STM32 PA10(RX), 共地
 *       OLED: PB8=SCL, PB9=SDA, 3.3V/GND 共地
 *
 * LED 调试:
 *   PC13 板载 LED (低电平点亮)
 *   上电快闪 3 次 → 证明 MCU 运行
 *   追踪中每收到一帧 toggle → 证明整条链路通
 *   无帧 / 丢目标 → LED 灭
 */

#include "stm32f10x.h"
#include "Delay.h"
#include "uart_parser.h"
#include "servo.h"
#include "pid.h"
#include "oled.h"
#include "usart3_config.h"

/* 全局解析器 (定义在 usart_config.c) */
extern uart_parser_t g_parser;

volatile uint32_t g_ms_tick = 0;

/* ===== 板载 LED ===== */
#define LED_PORT    GPIOC
#define LED_PIN     GPIO_Pin_13
#define LED_ON()    GPIO_ResetBits(LED_PORT, LED_PIN)  /* 低电平点亮 */
#define LED_OFF()   GPIO_SetBits(LED_PORT, LED_PIN)
#define LED_TOG()   (LED_PORT->ODR ^= LED_PIN)

/* ===== PID 参数 (像素 → 脉宽 us) ===== */
/* 画面 160x120(QQVGA), 偏差范围约 X±80px Y±60px        */
/* Pan(270°): 安全 600~2400us; Tilt(180°): 安全 1000~2400us */
/* 以下数值为 2026-08 实测整定结果 */
#define PAN_PID_KP  3.0f     /* Pan : 静止 MAE 1~8px, 移动 MAE 22~34px */
#define TILT_PID_KP 5.0f     /* Tilt: 静止 MAE 12px,  移动 MAE 15~19px */
/* 积分: 两轴需要的值不同, 所以拆成两个宏。
 * Pan 的负载轻, Ki=0.5 就够; Tilt 要抵抗重力, 静摩擦更大, 需要 Ki=1.0。
 * Ki 的作用是克服舵机静摩擦 —— 纯 P 控制时误差小->修正小->推不动舵机,
 * 于是永远留一个几十像素的静差 (实测 Pan 静止 MAE 45.9px)。
 * 加上积分后同一工况降到 8.3px。 */
#define PAN_PID_KI  0.5f
#define TILT_PID_KI 0.8f
/* 微分: 实测 0 最好。10fps 采样时 D 项会被 1/dt 放大, 反而引入抖动 */
#define PAN_PID_KD  0.0f
#define TILT_PID_KD 0.0f

/*
 * 修正量上限 (us)。上限决定了 PID 能"用出去"多少行程:
 *   饱和阈值 = OUT_MAX / Kp, 误差超过它就进入限幅, 再大的 Kp 也没用。
 * 早先 Tilt 只有 ±250us, Kp=1.5 时误差 167px 就饱和,
 * 一旦把 Kp 提到 3.0 以上, 阈值掉到 80px 以内, 加 Kp 的效果会被限幅吃掉,
 * 在线调参会误判成"加 Kp 无效"。
 * 现在放宽到与各自机械安全范围匹配:
 *   Pan : 1450 ± 750 → 700~2200us, 落在 600~2400 安全区内
 *   Tilt: 1500 ± 500 → 1000~2000us, 落在 1000~2400 安全区内
 * (注意: HOME 本身不居中, 上限受更近的那一侧边界约束)
 */
#define PAN_PID_OUT_MAX  750.0f   /* Pan 修正量上限, 约 ±101° */
#define TILT_PID_OUT_MAX 500.0f   /* Tilt 修正量上限 (us) */

/* 死区: ±3px 内不动作, 避免小误差引起抖动 */
#define DEADBAND_PX 3

/* 每帧脉宽最大变化量(us), 防止误差突变引起过冲振荡。
 * 注意: 这项是"每 10ms"的基准值, 实际步长会按真实 dt 折算 (见主循环),
 * 这样帧率变化时速度上限保持恒定, 而不是随帧率线性变化。 */
#define MAX_PULSE_STEP_US 60

/* 按时间折算后的单帧最大步长上限 (us)。
 * 这个值直接决定"能不能追上移动的目标":
 *   PID 算出的修正量若被它削平, 云台就会永远落后一截 —— 即使限幅还有余量。
 * 从 200 放宽到 350: 46fps 下 350us/帧 = 16100us/s (约 2400度/秒),
 * 远超人手持目标移动所需的转速, 因此大误差时不再被限速拖住。
 * 稳定性由 Kp/滤波/死区保证, 不靠限速兜底; 限速只防"误差突变时的猛冲"。 */
#define MAX_PULSE_STEP_US_MAX 350

/* dx/dy 一阶低通滤波系数 (0~1], 越大越灵敏、越小越平滑。
 * 设成 1.0 等于关闭滤波。
 *
 * 两轴分开设置, 因为它们的稳定性需求不同:
 *   Pan : 摄像头装在 Tilt 轴上, 但水平方向不受俯仰转动影响, 所以自环很弱,
 *         Kp=3.0 能长期稳定工作 -> 滤波可以弱一些, 保证响应速度。
 *   Tilt: 摄像头直接受本轴转动影响, 形成强自环(实测耦合 0.32px/us,
 *         Kp=6 时环路增益接近 2) -> 必须用更强的滤波来压低高频环路增益、
 *         换取相位裕度, 否则静止时就会自持摆动。
 * 0.2 在 46fps 下时间常数约 90ms, 对"手拿着目标上下动"这种低频运动
 * 影响很小, 但足以把摆动压掉。 */
#define FILTER_ALPHA_PAN   0.35f
#define FILTER_ALPHA_TILT  0.20f

/* 输入变化率限制 (px/帧): 单帧内 dx/dy 最多允许变化多少。
 * 真实目标由手移动时约 10~20px/帧 (46fps 下即 460~920px/s), 所以 40 不会
 * 拖慢正常跟踪; 但误识别造成的几十像素突跳会被卡住, 避免云台猛冲后
 * 摆动一秒才恢复。设成一个很大的值(如 500)等于关闭此保护。 */
#define MAX_TRACK_JUMP_PX 40.0f

/* 状态帧上报周期 (ms)。50ms = 20Hz。
 * 注意这不影响控制回路(控制跑在 OpenMV 帧率 46fps 上), 只影响上位机看到的
 * 数据密度。调参/排障时加密有助观察, 但也别太密 —— 115200 下每帧约 8.2ms。 */
#define STATUS_PERIOD_MS 50

/* 状态帧新鲜度门限: 超过这么久没收到新帧, 就认为目标已丢失。
 * OpenMV 正常帧率下 30~60ms 一帧, 200ms 足够容忍偶发丢帧。
 * 没有这道保护时, 目标丢失后仍会把最后一帧的 dx/dy 一直上报给上位机,
 * 在线调参会把"残留值"当成真实误差统计, 指标全被污染。 */
#define FRAME_TIMEOUT_MS 200

static void led_init(void)
{
    GPIO_InitTypeDef gpio;
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOC, ENABLE);
    gpio.GPIO_Pin   = LED_PIN;
    gpio.GPIO_Mode  = GPIO_Mode_Out_PP;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(LED_PORT, &gpio);
    LED_OFF();  /* 初始灭 */
}

static void led_startup_blink(void)
{
    for (int i = 0; i < 3; i++) {
        LED_ON();   Delay_ms(100);
        LED_OFF();  Delay_ms(100);
    }
}

int main(void)
{
    track_target_t target = {0, 0, 0};
    pid_t pid_pan, pid_tilt;
    uint16_t pan_pulse  = PAN_HOME_US;
    uint16_t tilt_pulse = TILT_HOME_US;
    int16_t abs_dx, abs_dy;
    uint8_t oled_div = 0;
    uint32_t last_frame_ms = 0;   /* 上一帧到达时刻, 用于算 dt 和判新鲜度 */
    uint8_t manual_mode       = 0;   /* 1=手动控制模式 (由 USART3 命令切换) */
    uint8_t manual_seq_cache  = 0;   /* 已下发的手动命令序号 */
    float   filt_dx = 0.0f;          /* 低通滤波后的 x 偏差 */
    float   filt_dy = 0.0f;          /* 低通滤波后的 y 偏差 */
    float   last_raw_dx = 0.0f;      /* 上一帧限速后的 dx (变化率限制用) */
    float   last_raw_dy = 0.0f;      /* 上一帧限速后的 dy */
    float   clamp_dx = 0.0f;         /* 本帧限速结果 */
    float   clamp_dy = 0.0f;
    uint8_t filt_init = 1;           /* 1=滤波器待初始化 (用第一帧直接置初值) */

    /* 阶段1: USART1 + 解析器初始化 */
    extern void usart1_init(void);
    usart1_init();

    /* LED 初始化 + 启动快闪 */
    led_init();
    led_startup_blink();

    /* 阶段2: 舵机 PWM 初始化 */
    servo_init();

    /* 阶段4: OLED 初始化 */
    oled_init();
    /* 上电先刷一屏, 便于确认 OLED 通信正常 */
    oled_show_tracking(0, 0, 0, PAN_HOME_US, TILT_HOME_US, 0);

    /* 阶段3: PID 初始化 (输出 = 偏离中点的脉宽修正量, us) */
    pid_init(&pid_pan,  PAN_PID_KP,  PAN_PID_KI,  PAN_PID_KD,  -PAN_PID_OUT_MAX,  PAN_PID_OUT_MAX);
    pid_init(&pid_tilt, TILT_PID_KP, TILT_PID_KI, TILT_PID_KD, -TILT_PID_OUT_MAX, TILT_PID_OUT_MAX);

    /* 阶段5: USART3 在线调参 (PB10/PB11 -> USB-TTL) */
    usart3_init(&pid_pan, &pid_tilt);

    /* 1ms 系统节拍, 供上位机定时回传使用 */
    (void)SysTick_Config(SystemCoreClock / 1000);

    /* 上电自检: Pan/Tilt 各扫一次, 肉眼确认舵机能动 */
    /* Pan 自检: 以正前方为中心左右摆动, 不再从 0°/270° 扫 */
    /* 每段都从正前方出发, 避免大摆幅时单程太长走不完 */
    /*servo_set_pan_us(PAN_HOME_US - PAN_SWEEP_OFFSET_US);  Delay_ms(400);
    servo_set_pan_us(PAN_HOME_US);                        Delay_ms(400);
    servo_set_pan_us(PAN_HOME_US + PAN_SWEEP_OFFSET_US);  Delay_ms(400);
    servo_set_pan_us(PAN_HOME_US);                        Delay_ms(400);*/
    /* Tilt 自检: 与 Pan 一致, 每段都从中位出发 */
    /*servo_set_tilt_us(TILT_HOME_US - TILT_SWEEP_OFFSET_US);  Delay_ms(400);
    servo_set_tilt_us(TILT_HOME_US);                         Delay_ms(400);
    servo_set_tilt_us(TILT_HOME_US + TILT_SWEEP_OFFSET_US);  Delay_ms(400);
    servo_set_tilt_us(TILT_HOME_US);                         Delay_ms(400);*/

    while (1)
    {
        /* ===== 手动模式: 脱离摄像头直接驱动舵机 (调试用) =====
         * 收到过 'pan xxx' 或 'tlt xxx' 就进入手动模式, 直到发 'auto' 才退出。
         * 手动模式下不跑 PID、不驱动舵机跟踪, 但【仍然要消费 OpenMV 的帧】:
         *   uart_parser 的 frame_ready 标志要靠主循环 consume 才会清掉,
         *   状态机也停在 FRAME_DONE 等消费。若不消费, 解析器就卡死,
         *   后续帧全部读不出来, 于是状态帧一直上报 DX/DY = 0 ——
         *   表现为"一切手动模式目标就丢失", 开环测试因此无法进行。
         * 用 if/else 而不是 goto+label: 标签后面的变量初始化若被 goto 跳过,
         * Keil (C89 规则) 会直接报错。 */
        if (usart3_manual_active())
        {
            if (!manual_mode) {
                manual_mode      = 1;
                manual_seq_cache = 0;    /* 强制下发第一条命令 */
            }
            /* 保持解析器畅通: 只消费、不使用, 让 DX/DY 能照常上报 */
            if (uart_parser_consume(&g_parser, &target)) {
                last_frame_ms = g_ms_tick;
            }
            /* 序号变了才重新写 PWM: 连续发多条 pan/tlt 都能生效 */
            if (usart3_manual_seq() != manual_seq_cache) {
                manual_seq_cache = usart3_manual_seq();
                pan_pulse  = usart3_manual_pan_us();
                tilt_pulse = usart3_manual_tilt_us();
                servo_set_pan_us(pan_pulse);
                servo_set_tilt_us(tilt_pulse);
                LED_OFF();
            }
        }
        else
        {
            if (manual_mode) {
                /* 刚退出手动模式: 复位 PID 与 dt 基准, 避免残留造成一次冲击 */
                manual_mode = 0;
                pid_reset(&pid_pan);
                pid_reset(&pid_tilt);
                last_frame_ms = g_ms_tick;
            }

            /* 轮询消费解析完成的帧 */
            if (uart_parser_consume(&g_parser, &target))
            {
            /* 收到新帧: 计算与上一帧的时间间隔, 供 PID 的积分/微分使用 */
            uint32_t now_ms = g_ms_tick;
            float dt = (float)(uint32_t)(now_ms - last_frame_ms) / 1000.0f;
            last_frame_ms = now_ms;

            /* 保护: 首帧或间隔异常(丢帧/中断被长时间阻塞)时退回 10ms,
             * 避免 dt=0 造成除零, 或 dt 过大把积分项一次推爆 */
            if (dt <= 0.0f || dt > 0.5f) {
                dt = 0.01f;
            }

            if (target.flag == 0x01) {
                /* 目标锁定: toggle LED, 运行 PID */
                LED_TOG();

                /*
                 * (1) 输入变化率限制 —— 抑制误识别造成的阶跃冲击。
                 *
                 * 场景: OpenMV 偶尔会把别的红色物体当成目标, 于是 dx/dy 从
                 * 当前值突然跳到几十像素外; 等它重新认出真目标, 又跳回来。
                 * 这种阶跃灌进 PID 会被 Kp 放大成几百 us 的猛冲, 同时 Ki
                 * 快速累积积分, 结果就是"重新锁定后先摆一秒才跟上"。
                 *
                 * 在滤波之前先把每帧变化量卡住: 超过 MAX_TRACK_JUMP_PX 的部分
                 * 直接丢弃。真实目标由手移动时每帧变化约 10~20px (46fps 下
                 * 相当于 460~920px/s, 已经比手快), 所以 40px/帧 的门限
                 * 不会拖慢正常跟踪, 但能挡住误识别那种几十像素的突跳。
                 */
                {
                    if (filt_init) {
                        /* 重新锁定后的第一帧: 直接用当前位置作基准, 不限速。
                         * 若这里也限速, 会凭空制造一个从 0 到真实位置的跳变,
                         * 反而拖慢恢复。跳变保护只用于之后的帧间比较。 */
                        clamp_dx = (float)target.dx;
                        clamp_dy = (float)target.dy;
                    } else {
                        float rd = (float)target.dx - last_raw_dx;
                        float ry = (float)target.dy - last_raw_dy;
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
                    /* 摄像头倒装, 仅 dx 取反 */
                    float corr_pan  = pid_update(&pid_pan,  0.0f, -filt_dx, dt);
                    float corr_tilt = pid_update(&pid_tilt, 0.0f,  filt_dy, dt);

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

                    pan_pulse  = (uint16_t)pan;
                    tilt_pulse = (uint16_t)tilt;

                    servo_set_pan_us(pan_pulse);
                    servo_set_tilt_us(tilt_pulse);
                }
            } else {
                /* 目标丢失: 灭灯, 复位 PID 与滤波器, 保持当前舵机位置。
                 * 滤波器也要复位: 否则下次重新锁定目标时, 会从旧位置
                 * 慢慢"爬"过去, 表现为一次明显的迟滞。 */
                LED_OFF();
                pid_reset(&pid_pan);
                pid_reset(&pid_tilt);
                filt_init = 1;
            }

            /* 每 8 帧刷新一次 OLED, 避免阻塞追踪主循环 */
            if ((++oled_div & 0x07) == 0) {
                oled_show_tracking(target.dx, target.dy,
                                   target.flag == 0x01,
                                   pan_pulse, tilt_pulse,
                                   g_parser.total_frames);
            }

        }
        }   /* end else (自动追踪) */

        /* 上位机请求或每 STATUS_PERIOD_MS 回传一次状态。
         * 从 100ms 缩到 50ms: 串口占用从 9% 提到 18% (115200 下每帧 94 字节
         * 约 8.2ms), 仍然安全, 但上位机看到的波形密度翻倍,
         * 调试和调参时更容易看清瞬态。 */
        static uint32_t last_status_ms = 0;
        if (usart3_status_requested()
            || (uint32_t)(g_ms_tick - last_status_ms) >= STATUS_PERIOD_MS) {
            last_status_ms = g_ms_tick;

            /*
             * 只在"目标锁定 且 本帧足够新"时上报真实偏差,
             * 否则上报 0。理由:
             *   目标丢失或帧超时后, target.dx/dy 仍是最后一帧的残留值,
             *   若原样上报, 上位机调参脚本无法区分"真实误差"和"残留值",
             *   统计出的 MAE / 符号翻转次数会被污染, AI 据此调参必然跑偏。
             * 舵机脉宽照常上报 (它反映真实输出, 即使目标丢失也保持位置)。
             */
            uint8_t fresh = (target.flag == 0x01)
                         && ((uint32_t)(g_ms_tick - last_frame_ms) < FRAME_TIMEOUT_MS);

            usart3_send_status(fresh ? target.dx : 0,
                               fresh ? target.dy : 0,
                               pan_pulse, tilt_pulse,
                               &pid_pan, &pid_tilt);
        }
    }
}
