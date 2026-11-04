#include "speed_axis.h"
uint16_t speed_axis_pulse(int16_t error, uint16_t neutral, int direction)
{
 int32_t offset;
 if (error >= -3 && error <= 3) return neutral;
 /* 0.1 us/pixel, rounded; hard commissioning cap, not a mechanical limit. */
 offset=error>0 ? (error+5)/10 : -((-error+5)/10);
 if(offset>PAN_SPEED_MAX_OFFSET_US)offset=PAN_SPEED_MAX_OFFSET_US;
 if(offset<-PAN_SPEED_MAX_OFFSET_US)offset=-PAN_SPEED_MAX_OFFSET_US;
 return (uint16_t)((int32_t)neutral+direction*offset);
}
