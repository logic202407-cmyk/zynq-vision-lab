`timescale 1ns/1ps
// Explicit operator ARM/AUTO, one fixed paper-target bench. No boot motion.
// AUTO executes the MCU-local OpenMV controller under FPGA lease supervision.
module c1_control_link #(parameter CLOCK_HZ=50000000,LOCAL_RESETS=1,CONTINUOUS_AUTO=0)(
 input wire clk,reset_n,camera_clk,camera_reset_n,
 input wire acquire,query,configure,stop_request,authorize,start_auto,
 input wire[127:0] query_id,input wire[63:0] logging_session,
 input wire mcu_rx,input wire camera_strobe,input wire[218:0] camera_snapshot,
 output wire mcu_tx,pc_tx,owner,fault,stop_confirmed,session_active,
 output wire[3:0] state,output wire[31:0] camera_dropped,measurement_dropped,
 output wire[1:0] pwm_mask,output wire[31:0] accepted_count);
 wire[15:0] pan,tilt;
 zynq_vision_link #(.CLOCK_HZ(CLOCK_HZ),.LOCAL_RESETS(LOCAL_RESETS),.ALLOW_AUTO(1),.CONTINUOUS_AUTO(CONTINUOUS_AUTO)) link(
 .clk(clk),.reset_n(reset_n),.camera_clk(camera_clk),.camera_reset_n(camera_reset_n),
 .query(query),.authorize(authorize&&session_active),.command(start_auto&&session_active),.stop_request(stop_request),
 .axis(2'b11),.pulse_us(16'd0),.epoch(query_id),.request_local(acquire),
 .pc_quiet_ack(acquire),.pc_rx(1'b1),.mcu_rx(mcu_rx),.configure(configure),
 .config_nonce(64'd0),.config_session(logging_session),
 .camera_strobe(camera_strobe),.camera_snapshot(camera_snapshot),
 .pc_tx(pc_tx),.mcu_tx(mcu_tx),.owner(owner),.fault(fault),
 .stop_confirmed(stop_confirmed),.session_active(session_active),.state(state),
 .accepted_count(accepted_count),.pan_target(pan),.tilt_target(tilt),.pwm_mask(pwm_mask),
 .camera_dropped(camera_dropped),.measurement_dropped(measurement_dropped));
endmodule
