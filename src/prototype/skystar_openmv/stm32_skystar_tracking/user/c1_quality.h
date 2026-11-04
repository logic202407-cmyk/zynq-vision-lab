#ifndef C1_QUALITY_H
#define C1_QUALITY_H
#include "vision_measurement.h"
/* Candidate control-quality floor, not a mechanical or optical calibration.
 * Raw M2 target_valid/count/bbox remain unchanged and continue to be logged. */
#ifndef C1_PRIMARY_MIN_PIXELS
#define C1_PRIMARY_MIN_PIXELS 32u
#endif
enum { C1_QUALITY_OK=0, C1_QUALITY_INCOMPLETE=1, C1_QUALITY_SPARSE=2,
       C1_QUALITY_EDGE=3, C1_QUALITY_GEOMETRY=4 };
static unsigned c1_primary_quality(const measurement_t *v)
{
    if ((v->flags&3u)!=3u) return C1_QUALITY_INCOMPLETE;
    if (v->width<3u || v->height<3u || v->xmin>v->xmax || v->ymin>v->ymax ||
        v->xmax>=v->width || v->ymax>=v->height ||
        v->cx<v->xmin || v->cx>v->xmax || v->cy<v->ymin || v->cy>v->ymax)
        return C1_QUALITY_GEOMETRY;
    if (v->count<C1_PRIMARY_MIN_PIXELS) return C1_QUALITY_SPARSE;
    if (!v->xmin || !v->ymin || v->xmax==v->width-1u || v->ymax==v->height-1u)
        return C1_QUALITY_EDGE;
    return C1_QUALITY_OK;
}
#endif
