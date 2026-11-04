`timescale 1ns/1ps
// Offline candidate: synchronous inputs, command is presented to the B2 FSM
// on the SAME edge used to test READY, eliminating a registered-pulse race.
// Rejected remains a one-cycle diagnostic. No authorization or PWM driver.
module c1_two_axis_step_gate_v2(
 input wire clk,reset_n,ready,
 input wire [1:0] axis_select,
 input wire step,center,
 output wire command,
 output reg rejected,
 output wire [1:0] axis,
 output wire [15:0] pulse_us
);
 reg old_step,old_center,inputs_clear;
 wire new_step=step&&!old_step;
 wire new_center=center&&!old_center;
 wire event_now=inputs_clear&&(new_step||new_center);
 wire valid_axis=(axis_select==2'd0)||(axis_select==2'd1);
 wire admissible=ready&&valid_axis&&!(step&&center);
 assign command=reset_n&&event_now&&admissible;
 assign axis=axis_select;
 assign pulse_us=new_step?16'd1550:16'd1500;
 always @(posedge clk or negedge reset_n)begin
  if(!reset_n)begin old_step<=0;old_center<=0;inputs_clear<=0;rejected<=0;end
  else begin
   old_step<=step;old_center<=center;rejected<=event_now&&!admissible;
   if(!inputs_clear&&!step&&!center)inputs_clear<=1;
  end
 end
endmodule
