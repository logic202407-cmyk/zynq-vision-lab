#include "circle_console.h"
#include "circle_draw.h"
#include "servo.h"
#include "laser.h"
#include <string.h>

extern volatile uint32_t g_ms_tick;
#define PI 3.14159265358979323846f
#define PAN_RATE (2000.0f / (PAN_SERVO_MAX_ANGLE * PI / 180.0f))
#define TILT_RATE (2000.0f / PI)

static circle_draw_t draw;
static uint8_t motors_ready, size_set;

static void send_text(const char *s)
{
    while (*s) {
        while (USART_GetFlagStatus(USART3, USART_FLAG_TXE) == RESET) { }
        USART_SendData(USART3, (uint8_t)*s++);
    }
}

static void console_init(void)
{
    GPIO_InitTypeDef gpio;
    USART_InitTypeDef uart;
    /* This test mode polls USART3. The tracking-mode RX interrupt is never enabled. */
    NVIC_DisableIRQ(USART3_IRQn);
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOB | RCC_APB2Periph_AFIO, ENABLE);
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_USART3, ENABLE);
    gpio.GPIO_Pin = GPIO_Pin_10;
    gpio.GPIO_Mode = GPIO_Mode_AF_PP;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOB, &gpio);
    gpio.GPIO_Pin = GPIO_Pin_11;
    gpio.GPIO_Mode = GPIO_Mode_IN_FLOATING;
    GPIO_Init(GPIOB, &gpio);
    USART_StructInit(&uart);
    uart.USART_BaudRate = 115200;
    uart.USART_Mode = USART_Mode_Rx | USART_Mode_Tx;
    USART_Init(USART3, &uart);
    USART_Cmd(USART3, ENABLE);
}

static void send_number(const char *label, uint32_t value)
{
    char buffer[12];
    unsigned index = sizeof(buffer) - 1U;
    buffer[index] = '\0';
    do { buffer[--index] = (char)('0' + value % 10U); value /= 10U; } while (value);
    send_text(label); send_text(&buffer[index]);
}

static void status(void)
{
    static const char *const names[] = {"IDLE", "MOVE", "SETTLE", "RUN", "CLOSE", "POINT"};
    send_text("STATE "); send_text(names[draw.state]);
    send_number(" READY ", motors_ready); send_number(" SIZE_SET ", size_set);
    send_number(" LASER ", draw.laser);
    send_number(" PAN ", draw.pan); send_number(" TLT ", draw.tilt);
    send_number(" D_MM ", (uint32_t)draw.config.distance_mm);
    send_number(" R_MM ", (uint32_t)draw.config.radius_mm);
    send_number(" T_MS ", draw.config.period_ms);
    send_number(" BACK ", draw.config.pan_back_us);
    send_number(" ", draw.config.tilt_back_us);
    send_number(" FAULT ", draw.timing_fault); send_text("\r\n");
}

static void start_job(circle_job_t job)
{
    if (!motors_ready) { send_text("ERR send home first\r\n"); return; }
    if ((job == CIRCLE_DRY || job == CIRCLE_DRAW || job == CIRCLE_SQUARE) && !size_set) {
        send_text("ERR set size D_mm R_mm T_ms first\r\n"); return;
    }
    send_text(circle_begin(&draw, job, g_ms_tick) ? "OK START\r\n" : "ERR invalid path\r\n");
}

static void command(const char *line)
{
    circle_config_t next = draw.config;
    float values[4];
    if (strcmp(line, "stop") == 0) {
        circle_stop(&draw);
        laser_off();
        send_text("OK STOP LASER 0\r\n");
    } else if (strcmp(line, "status") == 0 || strcmp(line, "st") == 0) {
        status();
    } else if (strcmp(line, "help") == 0) {
        send_text("home | center PAN_us TLT_us | point | size D_mm R_mm T_ms\r\n"
                  "scale PAN_gain TLT_gain | back PAN_us TLT_us | dry | draw\r\n"
                  "square (R_mm = half side) | line X1 Y1 X2 Y2 (mm) | stop | status\r\n");
    } else if (draw.state != CIRCLE_IDLE) {
        send_text("ERR busy; stop first\r\n");
    } else if (strcmp(line, "home") == 0) {
        if (!motors_ready) { servo_init(); motors_ready = 1; }
        start_job(CIRCLE_HOME);
    } else if (strcmp(line, "point") == 0) {
        start_job(CIRCLE_DOT);
    } else if (strcmp(line, "dry") == 0) {
        start_job(CIRCLE_DRY);
    } else if (strcmp(line, "draw") == 0) {
        start_job(CIRCLE_DRAW);
    } else if (strcmp(line, "square") == 0) {
        start_job(CIRCLE_SQUARE);
    } else if (circle_parse_signed_values(line, "line", values, 4)) {
        if (values[0] == values[2] && values[1] == values[3]) {
            send_text("ERR line zero length\r\n"); return;
        }
        next.line_x1 = values[0]; next.line_y1 = values[1];
        next.line_x2 = values[2]; next.line_y2 = values[3];
        if (!circle_line_valid(&next, &draw.limits)) { send_text("ERR line/range\r\n"); return; }
        draw.config = next;
        start_job(CIRCLE_LINE);
    } else if (circle_parse_values(line, "size", values, 3)) {
        if (!(values[2] >= 3000.0f && values[2] <= 30000.0f)) { send_text("ERR period\r\n"); return; }
        next.distance_mm = values[0]; next.radius_mm = values[1]; next.period_ms = (uint32_t)values[2];
        if (!circle_config_valid(&next, &draw.limits)) { send_text("ERR size/range\r\n"); return; }
        draw.config = next; size_set = 1; status();
    } else if (circle_parse_values(line, "center", values, 2)) {
        if (!motors_ready) { send_text("ERR send home first\r\n"); return; }
        if (!(values[0] >= PAN_SAFE_MIN && values[0] <= PAN_SAFE_MAX
           && values[1] >= TILT_SAFE_MIN && values[1] <= TILT_SAFE_MAX)) { send_text("ERR center\r\n"); return; }
        next.center_pan = (uint16_t)values[0]; next.center_tilt = (uint16_t)values[1];
        if (!circle_config_valid(&next, &draw.limits)) { send_text("ERR path limits\r\n"); return; }
        draw.config = next;
        start_job(CIRCLE_HOME);
    } else if (circle_parse_values(line, "scale", values, 2)) {
        next.pan_us_per_rad = PAN_RATE * values[0]; next.tilt_us_per_rad = TILT_RATE * values[1];
        if (!circle_config_valid(&next, &draw.limits)) { send_text("ERR scale/range\r\n"); return; }
        draw.config = next; send_text("OK SCALE\r\n");
    } else if (circle_parse_values(line, "back", values, 2)) {
        /* Reject out-of-range input before the float->uint16 cast can wrap. */
        if (!(values[0] <= 100.0f && values[1] <= 100.0f)) { send_text("ERR back/range\r\n"); return; }
        next.pan_back_us = (uint16_t)values[0]; next.tilt_back_us = (uint16_t)values[1];
        if (!circle_config_valid(&next, &draw.limits)) { send_text("ERR back/range\r\n"); return; }
        draw.config = next; send_text("OK BACK\r\n"); status();
    } else {
        send_text("ERR command; send help\r\n");
    }
}

void circle_console_run(void)
{
    circle_config_t cfg = {500.0f, 20.0f, PAN_RATE, TILT_RATE, 8000U,
                           PAN_HOME_US, TILT_HOME_US, 0U, 0U};
    circle_limits_t limits = {PAN_SAFE_MIN, PAN_SAFE_MAX, TILT_SAFE_MIN, TILT_SAFE_MAX};
    char line[80];
    uint8_t length = 0, discard = 0;
    uint16_t applied_pan = 0, applied_tilt = 0;
    uint32_t last_rx = 0;
    circle_state_t previous;

    circle_init(&draw, &cfg, &limits);
    console_init();
    (void)SysTick_Config(SystemCoreClock / 1000U);
    /* Do not use Delay_ms(): the old delay driver reconfigures SysTick. */
    send_text("LASER CIRCLE READY; motors/laser OFF; send help\r\n");
    for (;;) {
        uint32_t now = g_ms_tick;
        uint32_t sr = USART3->SR;
        if (sr & (USART_FLAG_ORE | USART_FLAG_FE | USART_FLAG_NE)) {
            (void)USART3->DR;
            length = 0; discard = 1;
            circle_stop(&draw); laser_off();
        } else if (sr & USART_FLAG_RXNE) {
            char ch = (char)USART_ReceiveData(USART3);
            last_rx = now;
            if (ch == '\r' || ch == '\n') {
                if (discard) send_text("ERR discarded serial line\r\n");
                else if (length) { line[length] = '\0'; command(line); }
                length = 0; discard = 0;
            } else if (!discard) {
                if (length < sizeof(line) - 1U && ((ch >= 32 && ch <= 126) || ch == '\t')) line[length++] = ch;
                else { length = 0; discard = 1; circle_stop(&draw); laser_off(); }
            }
        }
        if ((length || discard) && (uint32_t)(now - last_rx) > 1000U) {
            length = 0; discard = 0;
        }
        previous = draw.state;
        circle_tick(&draw, g_ms_tick);
        if (!draw.laser) laser_off();
        if (motors_ready && (draw.pan != applied_pan || draw.tilt != applied_tilt)) {
            /* Suppress TIM2 update events while loading both shadow registers. */
            TIM_UpdateDisableConfig(TIM2, ENABLE);
            servo_set_pan_us(draw.pan); servo_set_tilt_us(draw.tilt);
            TIM_UpdateDisableConfig(TIM2, DISABLE);
            applied_pan = draw.pan; applied_tilt = draw.tilt;
        }
        if (draw.laser) laser_on();
        if (previous != CIRCLE_IDLE && draw.state == CIRCLE_IDLE) {
            send_text(draw.timing_fault ? "ERR timing; LASER 0\r\n" : "DONE LASER 0\r\n");
        }
    }
}
