/* Host-only, read-only observations. The original adapter and DUT are included
 * unchanged in this translation unit; this file is never in the ARM project. */
#include "bridge.c"

EXPORT uint32_t p0_detail(unsigned field)
{
    switch (field) {
    case 0: return c.have_frame;
    case 1: return c.need_new_frame;
    case 2: return c.resume_ms;
    case 3: return c.now_ms;
    case 4: return p.used;
    case 5: return p.total_frames;
    case 6: return p.last_byte_ms;
    case 7: return (uint32_t)p.last_reject;
    default: return 0;
    }
}
