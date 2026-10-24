#include "stm32f10x.h"
#include "circle_console.h"
#include "laser.h"

volatile uint32_t g_ms_tick = 0;

int main(void)
{
    /* A reset leaves PWM disabled; only an explicit home starts the servos. */
    laser_init();
    circle_console_run();
    for (;;) {
        laser_off();
    }
}
