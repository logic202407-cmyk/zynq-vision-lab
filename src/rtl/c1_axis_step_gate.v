`timescale 1ns/1ps
// Offline operator gate. This does NOT arm, allocate QIDs or drive pins.
// Downstream STM32 single-axis commands can enable BOTH PWM channels.
module c1_axis_step_gate #(
 parameter integer AXIS = 0
)(
 input wire clk, reset_n, ready, step, center,
 output reg command,
 output reg [1:0] axis,
 output reg [15:0] pulse_us,
 output reg rejected
);
 reg old_step, old_center, inputs_clear;
 wire new_step=step && !old_step;
 wire new_center=center && !old_center;
 always @(posedge clk or negedge reset_n) begin
  if (!reset_n) begin
   old_step<=0; old_center<=0; inputs_clear<=0; command<=0; axis<=0; pulse_us<=1500; rejected<=0;
  end else begin
   old_step<=step; old_center<=center; command<=0; rejected<=0;
   if (!inputs_clear && !step && !center) inputs_clear<=1;
   if (inputs_clear && (new_step || new_center)) begin
    if (!ready || (AXIS != 0 && AXIS != 1) || (new_step && new_center)) rejected<=1;
    else begin
     axis<=AXIS; pulse_us<=new_step ? 16'd1550 : 16'd1500; command<=1;
    end
   end
  end
 end
endmodule
