#ifndef SKYSTAR_TRACKING_PROFILE_H
#define SKYSTAR_TRACKING_PROFILE_H
/* Opt-in port of teammate 50d49b4's R6 controller tuning to F407.
 * Retain this board's 1500us centre, 1300..1700us commissioning window,
 * verified feedback signs, explicit S1ACK1 start/lease/STOP, and F1 protocol.
 * No F103 peripheral code or automatic boot motion is imported.
 * The other mount's (-4,+10) laser calibration is not valid for this bench.
 */
#ifdef SKYSTAR_TEAM_PROFILE
#define TRACK_PAN_KI 3.0f
#define TRACK_TILT_KI 4.0f
#define TRACK_STEP_PER_10MS 1.0f
#define TRACK_STEP_MIN_US 1
#define TRACK_STEP_MAX_US 5
#define TRACK_PROFILE_LABEL " STATIC_SPOT_200MS_PWM_OFF"
#else
#define TRACK_PAN_KI 3.0f
#define TRACK_TILT_KI 4.0f
#define TRACK_STEP_PER_10MS 3.0f
#define TRACK_STEP_MIN_US 1
#define TRACK_STEP_MAX_US 15
#define TRACK_PROFILE_LABEL ""
#endif
#endif
