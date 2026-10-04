#ifndef P0_COMMAND_H
#define P0_COMMAND_H
#include "control.h"
typedef struct { char line[64]; uint8_t used, overflow; uint32_t rejected; } command_t;
void command_init(command_t *cmd);
/* 1=accepted complete command, -1=rejected, 0=incomplete/empty line. */
int command_feed(command_t *cmd, control_t *c, uint8_t byte);
#endif
