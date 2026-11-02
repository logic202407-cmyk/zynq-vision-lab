`timescale 1ns/1ps
// Board diagnostic boundary: no arm, position or loop-start input exists.
// PC TX is deliberately NOT an actuator bypass on this candidate. PC receives
// MCU telemetry, while explicit JTAG/VIO controls allow query/config/STOP only.
// Query IDs are diagnostic correlation, NOT a certified motion epoch provider.
module c1_observation_link #(parameter CLOCK_HZ=50000000,LOCAL_RESETS=0)(
 input wire clk,reset_n,camera_clk,camera_reset_n,
 input wire acquire,query,configure,stop_request,
 input wire[127:0] query_id,input wire[63:0] logging_session,
 input wire mcu_rx,input wire camera_strobe,input wire[218:0] camera_snapshot,
 output wire mcu_tx,pc_tx,owner,fault,stop_confirmed,session_active,
 output wire[3:0] state,output wire[31:0] camera_dropped,measurement_dropped);
 wire[31:0] accepted;wire[15:0] pan,tilt;wire[1:0] pwm;
 zynq_vision_link #(.CLOCK_HZ(CLOCK_HZ),.LOCAL_RESETS(LOCAL_RESETS)) link(
 .clk(clk),.reset_n(reset_n),.camera_clk(camera_clk),.camera_reset_n(camera_reset_n),
 .query(query),.authorize(1'b0),.command(1'b0),.stop_request(stop_request),
 .axis(2'b11),.pulse_us(16'd0),.epoch(query_id),.request_local(acquire),
 .pc_quiet_ack(acquire),.pc_rx(1'b1),.mcu_rx(mcu_rx),.configure(configure),
 .config_nonce(64'd0),.config_session(logging_session),
 .camera_strobe(camera_strobe),.camera_snapshot(camera_snapshot),
 .pc_tx(pc_tx),.mcu_tx(mcu_tx),.owner(owner),.fault(fault),
 .stop_confirmed(stop_confirmed),.session_active(session_active),.state(state),
 .accepted_count(accepted),.pan_target(pan),.tilt_target(tilt),.pwm_mask(pwm),
 .camera_dropped(camera_dropped),.measurement_dropped(measurement_dropped));
endmodule
