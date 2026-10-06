#include "command.h"
#include <string.h>

void command_init(command_t *cmd) { memset(cmd, 0, sizeof(*cmd)); }
static int number(const char *s, float *out, int integer_only)
{
    float v = 0, scale = 0.1f;
    unsigned digits = 0;
    while (*s == ' ' || *s == '\t') ++s;
    if (*s == '+') ++s;
    while (*s >= '0' && *s <= '9') {
        v = v * 10.0f + (float)(*s++ - '0');
        if (v > 65535.0f) return 0;
        ++digits;
    }
    if (*s == '.' && !integer_only) {
        ++s;
        while (*s >= '0' && *s <= '9') {
            v += (float)(*s++ - '0') * scale;
            scale *= 0.1f;
            ++digits;
        }
    }
    while (*s == ' ' || *s == '\t') ++s;
    if (!digits || *s) return 0;
    *out = v;
    return 1;
}
static int process(char *line, control_t *c)
{
    char *s = line;
    float value;
    while (*s) { if (*s >= 'A' && *s <= 'Z') *s += 'a' - 'A'; ++s; }
    if (!strcmp(line, "auto")) { control_auto(c); return 1; }
    if (!strcmp(line, "st")) return 1;
    if (strlen(line) < 4 || (line[3] != ' ' && line[3] != '\t')) return 0;
    if (!strncmp(line, "pan", 3) || !strncmp(line, "tlt", 3)) {
        if (!number(line + 4, &value, 1)) return 0;
        return control_manual(c, line[0] == 't', (uint16_t)value);
    }
    if ((line[0] == 'p' || line[0] == 't') && line[1] == 'k' &&
        (line[2] == 'p' || line[2] == 'i' || line[2] == 'd')) {
        pid_t *pid = line[0] == 'p' ? &c->pan_pid : &c->tilt_pid;
        if (!number(line + 4, &value, 0) || value > 50.0f) return 0;
        if (line[2] == 'p') pid->Kp = value;
        else if (line[2] == 'i') pid->Ki = value;
        else pid->Kd = value;
        /* A parameter change starts a new observation/control history. */
        control_parameters_changed(c);
        return 1;
    }
    return 0;
}
int command_feed(command_t *cmd, control_t *c, uint8_t byte)
{
    int accepted;
    if (byte != '\r' && byte != '\n') {
        if (!cmd->overflow && byte >= 32 && byte <= 126 && cmd->used < sizeof(cmd->line) - 1)
            cmd->line[cmd->used++] = (char)byte;
        else cmd->overflow = 1;
        return 0;
    }
    if (!cmd->used && !cmd->overflow) return 0;
    cmd->line[cmd->used] = 0;
    accepted = !cmd->overflow && process(cmd->line, c);
    cmd->used = cmd->overflow = 0;
    if (!accepted) { ++cmd->rejected; c->last_reject = REJECT_COMMAND; return -1; }
    return 1;
}
