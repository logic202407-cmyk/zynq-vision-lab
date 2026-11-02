/* Offline numeric capture replay. No MCU registers, UART or devices. */
#include <string.h>
#include "c1_quality.h"
#ifdef _WIN32
#define API __declspec(dllexport)
#else
#define API
#endif
API unsigned replay_quality(unsigned count,unsigned flags,unsigned width,unsigned height,
 unsigned xmin,unsigned ymin,unsigned xmax,unsigned ymax,unsigned cx,unsigned cy)
{
 measurement_t v;memset(&v,0,sizeof(v));v.count=count;v.flags=(uint8_t)flags;
 v.width=(uint16_t)width;v.height=(uint16_t)height;
 v.xmin=(uint16_t)xmin;v.ymin=(uint16_t)ymin;v.xmax=(uint16_t)xmax;v.ymax=(uint16_t)ymax;
 v.cx=(uint16_t)cx;v.cy=(uint16_t)cy;return c1_primary_quality(&v);
}
