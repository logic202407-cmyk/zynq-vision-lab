`timescale 1ns/1ps
// Offline PD12/PAN candidate. No AUTO, emitter, pins, or automatic boot motion.
// The existing MCU enables both PWM channels on a single-axis command.
module c1_pd12_control_link #(parameter CLOCK_HZ=50000000,LOCAL_RESETS=1)(
 input wire clk,reset_n,camera_clk,camera_reset_n,
 input wire acquire,query,configure,stop_request,authorize,step,center,
 input wire[127:0] query_id,input wire[63:0] logging_session,
 input wire mcu_rx,input wire camera_strobe,input wire[218:0] camera_snapshot,
 output wire mcu_tx,pc_tx,owner,fault,stop_confirmed,session_active,rejected,
 output wire[3:0] state,output wire[31:0] camera_dropped,measurement_dropped,
 output wire[1:0] pwm_mask,output wire[31:0] accepted_count,
 output wire[15:0] pan_target,tilt_target
);
 wire command;wire [1:0] axis;wire [15:0] pulse_us;
 c1_axis_step_gate #(.AXIS(0)) gate(
  .clk(clk),.reset_n(reset_n),.ready(owner && !fault && session_active && state==4),
  .step(step),.center(center),.command(command),.axis(axis),.pulse_us(pulse_us),.rejected(rejected));
 zynq_vision_link #(.CLOCK_HZ(CLOCK_HZ),.LOCAL_RESETS(LOCAL_RESETS),.ALLOW_AUTO(0)) link(
  .clk(clk),.reset_n(reset_n),.camera_clk(camera_clk),.camera_reset_n(camera_reset_n),
  .query(query),.authorize(authorize&&session_active),.command(command),.stop_request(stop_request),
  .axis(axis),.pulse_us(pulse_us),.epoch(query_id),.request_local(acquire),
  .pc_quiet_ack(acquire),.pc_rx(1'b1),.mcu_rx(mcu_rx),.configure(configure),
  .config_nonce(64'd0),.config_session(logging_session),.camera_strobe(camera_strobe),
  .camera_snapshot(camera_snapshot),.pc_tx(pc_tx),.mcu_tx(mcu_tx),.owner(owner),
  .fault(fault),.stop_confirmed(stop_confirmed),.session_active(session_active),.state(state),
  .accepted_count(accepted_count),.pan_target(pan_target),.tilt_target(tilt_target),
  .pwm_mask(pwm_mask),.camera_dropped(camera_dropped),.measurement_dropped(measurement_dropped));
endmodule
