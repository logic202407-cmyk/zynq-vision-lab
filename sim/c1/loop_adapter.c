/* Offline only: real USART2 IRQ receives each decoded OpenMV byte. */
#include "link_adapter.c"
API void model_vision_receive(unsigned byte,unsigned bad_stop){
 R(U2)=(1u<<5)|(bad_stop?2u:0u);R(U2+4)=byte;USART2_IRQHandler();R(U2)=0;
}
API unsigned loop_vision_frames(void){return observation_devices.devices[0].control.frames;}
API unsigned loop_other_outputs(void){return observation_devices.devices[1].control.outputs|observation_devices.devices[2].control.outputs;}
API unsigned loop_primary_count(void){return observations.camera[0].value.count;}
API unsigned loop_primary_cx(void){return observations.camera[0].value.cx;}
API unsigned loop_primary_quality(void){return c1_primary_quality(&observations.camera[0].value);}
