`timescale 1ns/1ps
// XSim/C bridge: AXIS placeholder is set by the offline runner.
module motion_c_bridge_tb(input wire mcu_rx,input wire [153:0] controls,
 output wire [104:0] bridge_sample);
 reg clk=0;always #5 clk=~clk;
 wire tx,pc_tx,owner,fault,stopped,rejected;wire [3:0] state;
 wire [31:0] accepted;wire [15:0] pan,tilt;wire [1:0] mask;
 reg [31:0] count=0,errors=0;reg [7:0] last=0;
 wire [31:0] status={accepted[15:0],7'b0,mask,stopped,fault,owner,state};
 assign bridge_sample={count,last,errors,status,tx};
 c1_axis_step_link #(.AXIS(AXIS_VALUE)) dut(
  .clk(clk),.reset_n(controls[0]),.query(controls[1]),.authorize(controls[2]),
  .step(controls[3] && controls[22:7]==1550),
  .center(controls[3] && controls[22:7]==1500),.stop_request(controls[4]),
  .epoch(controls[150:23]),.request_local(controls[151]),.pc_quiet_ack(controls[152]),
  .pc_rx(controls[153]),.mcu_rx(mcu_rx),.pc_tx(pc_tx),.mcu_tx(tx),
  .owner(owner),.fault(fault),.stop_confirmed(stopped),.rejected(rejected),
  .state(state),.accepted_count(accepted),.pan_target(pan),.tilt_target(tilt),.pwm_mask(mask));
 always @(posedge clk) if(controls[0]) begin
  if(dut.motion.rv) begin count<=count+1;last<=dut.motion.rd;end
  if(dut.motion.re) errors<=errors+1;
 end
endmodule
