`timescale 1ns/1ps
// Offline two-axis manual calibration candidate; no AUTO or optical output.
// Single-axis commands still enable both STM32 PWM channels.
module c1_two_axis_step_link_guarded #(parameter CLOCK_HZ=50000000,LOCAL_RESETS=1)(
 input wire clk,reset_n,camera_clk,camera_reset_n,
 input wire acquire,query,configure,stop_request,authorize,step,center,
 input wire[1:0] axis_select,
 input wire[127:0] query_id,input wire[63:0] logging_session,
 input wire mcu_rx,input wire camera_strobe,input wire[218:0] camera_snapshot,
 output wire mcu_tx,pc_tx,owner,fault,stop_confirmed,session_active,rejected,
 output wire[3:0] state,output wire[31:0] camera_dropped,measurement_dropped,
 output wire[1:0] pwm_mask,output wire[31:0] accepted_count,
 output wire[15:0] pan_target,tilt_target,output reg[31:0] rejected_count
);
 wire command,command_ready;wire [1:0] axis;wire [15:0] pulse_us;
 // Persist rejection diagnostics so software does not miss a one-cycle pulse.
 always @(posedge clk or negedge reset_n)begin
  if(!reset_n)rejected_count<=0;
  else if(rejected&&rejected_count!=32'hffffffff)rejected_count<=rejected_count+1;
 end
 c1_two_axis_step_gate_v2 gate(
  .clk(clk),.reset_n(reset_n),.ready(command_ready && session_active && acquire && !stop_request),
  .axis_select(axis_select),.step(step),.center(center),.command(command),
  .axis(axis),.pulse_us(pulse_us),.rejected(rejected));
 zynq_vision_link_guarded #(.CLOCK_HZ(CLOCK_HZ),.LOCAL_RESETS(LOCAL_RESETS),.ALLOW_AUTO(0)) link(
  .clk(clk),.reset_n(reset_n),.camera_clk(camera_clk),.camera_reset_n(camera_reset_n),
  .query(query),.authorize(authorize&&session_active),.command(command),.stop_request(stop_request),
  .axis(axis),.pulse_us(pulse_us),.epoch(query_id),.request_local(acquire),
  .pc_quiet_ack(acquire),.pc_rx(1'b1),.mcu_rx(mcu_rx),.configure(configure),
  .config_nonce(64'd0),.config_session(logging_session),.camera_strobe(camera_strobe),
  .camera_snapshot(camera_snapshot),.pc_tx(pc_tx),.mcu_tx(mcu_tx),.owner(owner),
  .fault(fault),.stop_confirmed(stop_confirmed),.session_active(session_active),.state(state),
  .accepted_count(accepted_count),.pan_target(pan_target),.tilt_target(tilt_target),
  .pwm_mask(pwm_mask),.camera_dropped(camera_dropped),.measurement_dropped(measurement_dropped),.command_ready(command_ready));
endmodule
