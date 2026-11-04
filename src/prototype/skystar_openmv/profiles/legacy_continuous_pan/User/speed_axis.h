#ifndef SPEED_AXIS_H
#define SPEED_AXIS_H
#include <stdint.h>
/* Nominal neutral, NOT a measured stop calibration. Servo type confirmed by user.
 * Speed command, no position baseline, accumulated integral or historical slew. */
#define PAN_SPEED_NEUTRAL_US 1500u
#define PAN_SPEED_MAX_OFFSET_US 8
uint16_t speed_axis_pulse(int16_t error, uint16_t neutral, int direction);
#endif
