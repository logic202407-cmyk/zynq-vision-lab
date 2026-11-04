`timescale 1ns/1ps
// Laser-free optional integration. Top-level control/config inputs are synchronous.
// Signs default to disabled; real mechanical calibration is NOT supplied here.
module zynq_gimbal1_loop_runtime #(
 parameter CLOCK_HZ=100000000,BAUD=115200,LOCAL_RESETS=0
)(input wire clk,reset_n,camera_clk,camera_reset_n,
 input wire query,authorize,stop_request,loop_start,single_scene_confirmed,
 input wire[1:0] pan_direction,tilt_direction,
 input wire[127:0] epoch,input wire request_local,pc_quiet_ack,pc_rx,mcu_rx,
 input wire configure,input wire[63:0] config_nonce,config_session,
 input wire camera_strobe,input wire[218:0] camera_snapshot,
 output wire pc_tx,mcu_tx,owner,fault,stop_confirmed,session_active,
 output wire[3:0] state,output wire[31:0] accepted_count,
 output wire[15:0] pan_target,tilt_target,output wire[1:0] pwm_mask,
 output wire[31:0] camera_dropped,measurement_dropped,
 output wire loop_active,loop_fault,centered,output wire[31:0] feedback_count);
 wire generated_command,generated_stop,command_ready;wire[1:0] axis;wire[15:0] pulse;
 gimbal1_visual_loop_runtime #(.CLOCK_HZ(CLOCK_HZ),.BAUD(BAUD)) loop_control(
 clk,reset_n,loop_start,single_scene_confirmed,session_active,pan_direction,tilt_direction,config_session,mcu_rx,state,fault,command_ready,stop_request,
 pan_target,tilt_target,generated_command,axis,pulse,generated_stop,loop_active,loop_fault,centered,feedback_count);
 zynq_vision_link_guarded #(.CLOCK_HZ(CLOCK_HZ),.BAUD(BAUD),.LOCAL_RESETS(LOCAL_RESETS)) link(clk,reset_n,camera_clk,camera_reset_n,
 query,authorize,generated_command,stop_request||generated_stop,axis,pulse,epoch,
 request_local,pc_quiet_ack,pc_rx,mcu_rx,configure,config_nonce,config_session,camera_strobe,camera_snapshot,
 pc_tx,mcu_tx,owner,fault,stop_confirmed,session_active,state,accepted_count,pan_target,tilt_target,pwm_mask,
 camera_dropped,measurement_dropped,command_ready);
endmodule
