/* Host-only model of the production foreground; no physical device access. */
#define model_init original_init
#define model_foreground original_foreground
#include "../cosim/stm32_adapter.c"
#undef model_init
#undef model_foreground
API void model_init(void) {
    original_init(); laser_lock_reset(&port_laser);
    gimbal_registry_init(&observation_devices);memset(&observations,0,sizeof(observations));
}
API void model_foreground(void) {
    original_foreground();
    c1_expire(board_ms());
    board_laser_set(laser_lock_tick(&port_laser,board_ms(),
        (uint8_t)(guardian.state==SAFE_AUTO && control.valid && control.outputs)));
}
API void model_vision(int dx,int dy,unsigned valid) {
    unsigned i;uint8_t p[8]={0xaa,0xff,(uint8_t)dx,(uint8_t)(dx>>8),
        (uint8_t)dy,(uint8_t)(dy>>8),(uint8_t)valid,0xee};
    for(i=0;i<8;i++) {R(U2)=1u<<5;R(U2+4)=p[i];USART2_IRQHandler();R(U2)=0;}
}
API void model_key(unsigned v) { R(GPIOA+0x10)=v; }
API unsigned model_team_gains(void) {
    return control.pan_pid.Ki==3.0f && control.tilt_pid.Ki==4.0f;
}
