#include "../cosim/stm32_adapter.c"
API void c1_init(void){
 model_init();gimbal_registry_init(&observation_devices);memset(&observations,0,sizeof(observations));
 measurement_bind(&observations,0,0,1);
 observation_nonce_hi=guardian.nonce_hi;observation_nonce_lo=guardian.nonce_lo;
}
API unsigned c1_accepted(void){return observations.camera[0].accepted;}
API unsigned c1_flags(void){return observations.camera[0].value.flags;}
API unsigned c1_centroid_x(void){return observations.camera[0].value.cx;}
API unsigned c1_centroid_y(void){return observations.camera[0].value.cy;}
API unsigned c1_gaps(void){return observations.camera[0].gaps;}
API unsigned c1_fresh(void){measurement_tick(&observations,board_ms());return observations.camera[0].fresh;}
API void c1_openmv(unsigned byte){R(U2)=1u<<5;R(U2+4)=byte;USART2_IRQHandler();R(U2)=0;model_foreground();}
API unsigned c1_openmv_valid(void){return observation_devices.devices[0].control.valid;}
