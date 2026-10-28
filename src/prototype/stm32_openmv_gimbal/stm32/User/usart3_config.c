/**
 * @file    usart3_config.c
 * @brief   USART3 在线调参: 接收上位机命令, 实时修改 Kp/Ki/Kd
 *
 * 接线:
 *   STM32 PB10(TX) -> USB-TTL RX
 *   STM32 PB11(RX) <- USB-TTL TX
 *   GND 共地
 *
 * 命令 (换行结尾):
 *   pkp 4.00 / pki 0.00 / pkd 0.50   Pan
 *   tkp 1.50 / tki 0.00 / tkd 0.50   Tilt
 *   st                                请求一帧状态
 */

#include "usart3_config.h"
#include "stm32f10x.h"

#define CMD_BUF_SIZE 64

static pid_t *s_pan_pid = 0;
static pid_t *s_tilt_pid = 0;
static volatile char s_cmd[CMD_BUF_SIZE];
static volatile uint8_t s_cmd_len = 0;
static volatile uint8_t s_status_request = 0;

/* ===== 手动控制 (调试用: 脱离摄像头直接驱动舵机) ===== */
static volatile uint8_t  s_manual      = 0;      /* 1=手动模式, 不跑 PID */
static volatile uint16_t s_manual_pan  = 1500;   /* 手动脉宽 (us) */
static volatile uint16_t s_manual_tilt = 1500;
/* 每条手动命令都让序号 +1; main 循环发现序号变了就重新下发一次脉宽。
 * 早期版本用一个 manual_pulse_sent 布尔量, 结果第一条 pan 命令之后
 * 该标志永远为 1, 后续手动命令全部被忽略 (只能动一次)。 */
static volatile uint8_t  s_cmd_seq     = 0;

/* 与 servo.h 的安全范围保持一致 (此处不 include servo.h, 避免多一层依赖) */
#define PAN_US_MIN   600
#define PAN_US_MAX   2400
#define TILT_US_MIN  1000
#define TILT_US_MAX  2400

static uint16_t clamp_us(int32_t v, int32_t lo, int32_t hi)
{
    if (v < lo) return (uint16_t)lo;
    if (v > hi) return (uint16_t)hi;
    return (uint16_t)v;
}

static void uart3_putc(char c)
{
    while (USART_GetFlagStatus(USART3, USART_FLAG_TXE) == RESET);
    USART_SendData(USART3, (uint8_t)c);
}

static void uart3_puts(const char *s)
{
    while (*s != '\0') {
        uart3_putc(*s++);
    }
}

static void uart3_put_u32(uint32_t v)
{
    char buf[12];
    uint8_t i = 0;
    do {
        buf[i++] = (char)('0' + (v % 10));
        v /= 10;
    } while (v > 0);
    while (i > 0) uart3_putc(buf[--i]);
}

static void uart3_put_i32(int32_t v)
{
    uint32_t u;
    if (v < 0) {
        uart3_putc('-');
        u = (uint32_t)(-v);
    } else {
        u = (uint32_t)v;
    }
    uart3_put_u32(u);
}

static void uart3_put_f100(float v)
{
    int32_t x = (int32_t)(v * 100.0f + (v >= 0.0f ? 0.5f : -0.5f));
    uart3_put_i32(x);
}

static const char *skip_space(const char *s)
{
    while (*s == ' ' || *s == '\t') s++;
    return s;
}

static int parse_float(const char *s, float *out)
{
    float sign = 1.0f, val = 0.0f, frac = 0.0f, scale = 0.1f;
    int digits = 0;

    if (*s == '-') {
        sign = -1.0f;
        s++;
    } else if (*s == '+') {
        s++;
    }

    while (*s >= '0' && *s <= '9') {
        val = val * 10.0f + (float)(*s - '0');
        s++;
        digits = 1;
    }

    if (*s == '.') {
        s++;
        while (*s >= '0' && *s <= '9') {
            frac += (float)(*s - '0') * scale;
            scale *= 0.1f;
            s++;
            digits = 1;
        }
    }

    if (!digits) return 0;
    *out = sign * (val + frac);
    return 1;
}

static int cmd_prefix(const char *line, const char *cmd)
{
    while (*cmd != '\0') {
        if (*line != *cmd) return 0;
        line++;
        cmd++;
    }
    return (*line == ' ' || *line == '\t' || *line == '\0');
}

static void line_lower(char *s)
{
    while (*s != '\0') {
        if (*s >= 'A' && *s <= 'Z') *s = (char)(*s + 32);
        s++;
    }
}

static void cmd_process(char *line)
{
    float v;

    line_lower(line);

    if (cmd_prefix(line, "pkp") && parse_float(skip_space(line + 3), &v)) {
        s_pan_pid->Kp = v;
        s_status_request = 1;
    } else if (cmd_prefix(line, "pki") && parse_float(skip_space(line + 3), &v)) {
        s_pan_pid->Ki = v;
        s_status_request = 1;
    } else if (cmd_prefix(line, "pkd") && parse_float(skip_space(line + 3), &v)) {
        s_pan_pid->Kd = v;
        s_status_request = 1;
    } else if (cmd_prefix(line, "tkp") && parse_float(skip_space(line + 3), &v)) {
        s_tilt_pid->Kp = v;
        s_status_request = 1;
    } else if (cmd_prefix(line, "tki") && parse_float(skip_space(line + 3), &v)) {
        s_tilt_pid->Ki = v;
        s_status_request = 1;
    } else if (cmd_prefix(line, "tkd") && parse_float(skip_space(line + 3), &v)) {
        s_tilt_pid->Kd = v;
        s_status_request = 1;
    } else if (cmd_prefix(line, "pan") && parse_float(skip_space(line + 3), &v)) {
        /* 手动给定 Pan 脉宽: 进手动模式并停用 PID */
        s_manual_pan = clamp_us((int32_t)v, PAN_US_MIN, PAN_US_MAX);
        s_manual     = 1;
        s_cmd_seq++;                 /* 通知 main 立刻下发 */
        s_status_request = 1;
    } else if (cmd_prefix(line, "tlt") && parse_float(skip_space(line + 3), &v)) {
        s_manual_tilt = clamp_us((int32_t)v, TILT_US_MIN, TILT_US_MAX);
        s_manual      = 1;
        s_cmd_seq++;
        s_status_request = 1;
    } else if (cmd_prefix(line, "auto")) {
        /* 退出手动模式, 回到 OpenMV 追踪 */
        s_manual = 0;
        s_cmd_seq++;
        s_status_request = 1;
    } else if (cmd_prefix(line, "st")) {
        s_status_request = 1;
    }
}

uint8_t usart3_manual_active(void)
{
    return s_manual;
}

uint16_t usart3_manual_pan_us(void)
{
    return s_manual_pan;
}

uint16_t usart3_manual_tilt_us(void)
{
    return s_manual_tilt;
}

uint8_t usart3_manual_seq(void)
{
    return s_cmd_seq;
}

void usart3_init(pid_t *pan_pid, pid_t *tilt_pid)
{
    GPIO_InitTypeDef  gpio;
    USART_InitTypeDef usart;
    NVIC_InitTypeDef  nvic;

    s_pan_pid  = pan_pid;
    s_tilt_pid = tilt_pid;

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOB | RCC_APB2Periph_AFIO, ENABLE);
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_USART3, ENABLE);

    /* PB10 = USART3_TX, PB11 = USART3_RX */
    gpio.GPIO_Pin   = GPIO_Pin_10;
    gpio.GPIO_Mode  = GPIO_Mode_AF_PP;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOB, &gpio);

    gpio.GPIO_Pin  = GPIO_Pin_11;
    gpio.GPIO_Mode = GPIO_Mode_IN_FLOATING;
    GPIO_Init(GPIOB, &gpio);

    usart.USART_BaudRate            = 115200;
    usart.USART_WordLength          = USART_WordLength_8b;
    usart.USART_StopBits            = USART_StopBits_1;
    usart.USART_Parity              = USART_Parity_No;
    usart.USART_HardwareFlowControl = USART_HardwareFlowControl_None;
    usart.USART_Mode                = USART_Mode_Rx | USART_Mode_Tx;
    USART_Init(USART3, &usart);

    USART_ITConfig(USART3, USART_IT_RXNE, ENABLE);

    nvic.NVIC_IRQChannel                   = USART3_IRQn;
    nvic.NVIC_IRQChannelPreemptionPriority = 1;
    nvic.NVIC_IRQChannelSubPriority        = 1;
    nvic.NVIC_IRQChannelCmd                = ENABLE;
    NVIC_Init(&nvic);

    USART_Cmd(USART3, ENABLE);
}

uint8_t usart3_status_requested(void)
{
    uint8_t r = s_status_request;
    s_status_request = 0;
    return r;
}

void usart3_send_status(int16_t dx, int16_t dy,
                        uint16_t pan_us, uint16_t tilt_us,
                        const pid_t *pan_pid, const pid_t *tilt_pid)
{
    uart3_puts("DX ");
    uart3_put_i32(dx);
    uart3_puts(" DY ");
    uart3_put_i32(dy);
    uart3_puts(" PAN ");
    uart3_put_u32(pan_us);
    uart3_puts(" TLT ");
    uart3_put_u32(tilt_us);
    uart3_puts(" PKP ");
    uart3_put_f100(pan_pid->Kp);
    uart3_puts(" PKI ");
    uart3_put_f100(pan_pid->Ki);
    uart3_puts(" PKD ");
    uart3_put_f100(pan_pid->Kd);
    uart3_puts(" TKP ");
    uart3_put_f100(tilt_pid->Kp);
    uart3_puts(" TKI ");
    uart3_put_f100(tilt_pid->Ki);
    uart3_puts(" TKD ");
    uart3_put_f100(tilt_pid->Kd);
    uart3_puts("\r\n");
}

void USART3_IRQHandler(void)
{
    if (USART_GetITStatus(USART3, USART_IT_RXNE) != RESET) {
        uint8_t byte = (uint8_t)USART_ReceiveData(USART3);

        if (byte == '\n' || byte == '\r') {
            if (s_cmd_len > 0) {
                char line[CMD_BUF_SIZE];
                uint8_t i;
                for (i = 0; i < s_cmd_len; i++) {
                    line[i] = (char)s_cmd[i];
                }
                line[s_cmd_len] = '\0';
                s_cmd_len = 0;
                cmd_process(line);
            }
        } else if (s_cmd_len < CMD_BUF_SIZE - 1) {
            s_cmd[s_cmd_len++] = (char)byte;
        }
    }

    if (USART_GetITStatus(USART3, USART_IT_ORE) != RESET) {
        (void)USART3->SR;
        (void)USART3->DR;
    }
}
