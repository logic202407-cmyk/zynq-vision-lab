#ifndef P0_SERVO_H
#define P0_SERVO_H
#include "control.h"
/* Inherited prototype pins/ranges; final fixed-camera calibration is pending. */
void servo_init(void);
void servo_set_pan_us(int32_t pulse_us);
void servo_set_tilt_us(int32_t pulse_us);
#endif
