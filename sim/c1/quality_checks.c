#include <stdio.h>
#include <string.h>
#include "c1_quality.h"
static unsigned checks;
#define CHECK(expression) do{checks++;if(!(expression)){printf("FAIL line %u\n",(unsigned)__LINE__);return 1;}}while(0)
int main(void)
{
    measurement_t v,base;memset(&base,0,sizeof(base));
    base.flags=3;base.width=640;base.height=480;base.count=64;
    base.xmin=10;base.ymin=10;base.xmax=17;base.ymax=17;base.cx=13;base.cy=13;
    CHECK(c1_primary_quality(&base)==C1_QUALITY_OK);
    v=base;v.count=32;CHECK(c1_primary_quality(&v)==C1_QUALITY_OK);
    v=base;v.count=31;CHECK(c1_primary_quality(&v)==C1_QUALITY_SPARSE);
    v=base;v.xmin=0;CHECK(c1_primary_quality(&v)==C1_QUALITY_EDGE);
    v=base;v.ymin=0;CHECK(c1_primary_quality(&v)==C1_QUALITY_EDGE);
    v=base;v.xmax=639;CHECK(c1_primary_quality(&v)==C1_QUALITY_EDGE);
    v=base;v.ymax=479;CHECK(c1_primary_quality(&v)==C1_QUALITY_EDGE);
    v=base;v.flags=1;CHECK(c1_primary_quality(&v)==C1_QUALITY_INCOMPLETE);
    v=base;v.xmin=18;CHECK(c1_primary_quality(&v)==C1_QUALITY_GEOMETRY);
    v=base;v.cx=18;CHECK(c1_primary_quality(&v)==C1_QUALITY_GEOMETRY);
    v=base;v.width=2;CHECK(c1_primary_quality(&v)==C1_QUALITY_GEOMETRY);
    v=base;v.xmax=640;CHECK(c1_primary_quality(&v)==C1_QUALITY_GEOMETRY);
    printf("PASS %u C1 control quality checks; raw measurements unchanged\n",checks);return 0;
}
