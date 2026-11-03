/* Host-only probe: synthetic registers; no debug, serial or actuator access. */
#include "loop_adapter.c"

API void feedback_probe_reset(void)
{
    model_init();
    feedback_last_ms=observation_nonce_hi=observation_nonce_lo=0;
}
API void feedback_probe_key(unsigned high) { R(GPIOA+0x10)=high?1u:0u; }
API unsigned feedback_probe_tx_free(void) { return board_tx_free(); }
