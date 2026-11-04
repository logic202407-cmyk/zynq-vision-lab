`timescale 1ns/1ps
// Offline manual-step candidate; no board pins, vision, laser or boot motion.
// All operator inputs must be synchronized/debounced in the eventual board top.
// MCU single-axis commands still enable BOTH PWM channels.
module c1_axis_step_link #(
 parameter integer CLOCK_HZ=100000000, BAUD=115200, AXIS=0, AUTH_MS=30000
)(
 input wire clk,reset_n,query,authorize,step,center,stop_request,
 input wire [127:0] epoch,
 input wire request_local,pc_quiet_ack,pc_rx,mcu_rx,
 output wire pc_tx,mcu_tx,owner,fault,stop_confirmed,rejected,
 output wire [3:0] state,output wire [31:0] accepted_count,
 output wire [15:0] pan_target,tilt_target,output wire [1:0] pwm_mask
);
 wire command;wire [1:0] axis;wire [15:0] pulse;
 c1_axis_step_gate #(.AXIS(AXIS)) gate(
  .clk(clk),.reset_n(reset_n),.ready(owner && !fault && state==4),
  .step(step),.center(center),.command(command),.axis(axis),.pulse_us(pulse),.rejected(rejected));
 zynq_motion_s1 #(.CLOCK_HZ(CLOCK_HZ),.BAUD(BAUD),.AUTH_MS(AUTH_MS)) motion(
  .clk(clk),.reset_n(reset_n),.query(query),.authorize(authorize),.command(command),
  .stop_request(stop_request),.axis(axis),.pulse_us(pulse),.epoch(epoch),
  .request_local(request_local),.pc_quiet_ack(pc_quiet_ack),.pc_rx(pc_rx),.mcu_rx(mcu_rx),
  .pc_tx(pc_tx),.mcu_tx(mcu_tx),.owner(owner),.fault(fault),.stop_confirmed(stop_confirmed),
  .state(state),.accepted_count(accepted_count),.pan_target(pan_target),
  .tilt_target(tilt_target),.pwm_mask(pwm_mask));
endmodule
