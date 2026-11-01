/* Same real-C bridge as B2; reset C1 observation state, never pre-bind a session. */
#define model_init base_model_init
#define model_reboot base_model_reboot
#define model_foreground base_model_foreground
#include "../cosim/stm32_adapter.c"
#undef model_init
#undef model_reboot
#undef model_foreground
static void clear_observations(void){gimbal_registry_init(&observation_devices);memset(&observations,0,sizeof(observations));}
API void model_init(void){base_model_init();clear_observations();}
API void model_reboot(void){base_model_reboot();clear_observations();}
API void model_foreground(void){base_model_foreground();c1_expire(board_ms());}
API unsigned c1_accepted(void){return observations.camera[0].accepted;}
API unsigned c1_sequence(void){return observations.camera[0].value.sequence;}
API unsigned c1_session(void){return observations.camera[0].session_lo;}
API unsigned c1_bound(void){return observations.camera[0].session_bound;}
