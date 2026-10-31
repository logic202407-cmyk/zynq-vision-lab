`timescale 1ns/1ps
module motion_c_bridge_tb #(parameter AUTH_TEST_MS=30000)(input wire mcu_rx,input wire [153:0] controls,
 output wire [104:0] bridge_sample);
 reg clk=0;always #5 clk=~clk;
 wire tx,pc_tx,owner,fault,stopped;wire [3:0] state;
 wire [31:0] accepted;wire [15:0] pan,tilt;wire [1:0] mask;
 reg [31:0] count=0,errors=0;reg [7:0] last=0;
 wire [31:0] status={accepted[15:0],7'b0,mask,stopped,fault,owner,state};
 assign bridge_sample={count,last,errors,status,tx};
 zynq_motion_s1 #(.AUTH_MS(AUTH_TEST_MS)) dut(clk,controls[0],controls[1],controls[2],controls[3],controls[4],
 controls[6:5],controls[22:7],controls[150:23],controls[151],controls[152],controls[153],
 mcu_rx,pc_tx,tx,owner,fault,stopped,state,accepted,pan,tilt,mask);
 always @(posedge clk) if(controls[0]) begin
 if(dut.rv) begin count<=count+1;last<=dut.rd;end
 if(dut.re) errors<=errors+1;
 end
endmodule
