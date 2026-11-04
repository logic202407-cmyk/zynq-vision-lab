`timescale 1ns/1ps
// Offline manual calibration candidate. Not a visual controller or PWM driver.
// Inputs must be synchronous to clk; downstream MCU enables both PWM channels.
module c1_two_axis_step_gate(
 input wire clk, reset_n, ready,
 input wire [1:0] axis_select,
 input wire step, center,
 output reg command, rejected,
 output reg [1:0] axis,
 output reg [15:0] pulse_us
);
 reg old_step, old_center, inputs_clear;
 wire new_step = step && !old_step;
 wire new_center = center && !old_center;
 always @(posedge clk or negedge reset_n) begin
  if (!reset_n) begin
   old_step<=0; old_center<=0; inputs_clear<=0;
   command<=0; rejected<=0; axis<=0; pulse_us<=1500;
  end else begin
   old_step<=step; old_center<=center; command<=0; rejected<=0;
   if (!inputs_clear && !step && !center) inputs_clear<=1;
   if (inputs_clear && (new_step || new_center)) begin
    if (!ready || axis_select>1 || (step && center)) rejected<=1;
    else begin
     axis<=axis_select;
     pulse_us<=new_step ? 16'd1550 : 16'd1500;
     command<=1;
    end
   end
  end
 end
endmodule
