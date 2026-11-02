`timescale 1ns/1ps
module b3_gate_bridge_tb(input wire mcu_rx,input wire [153:0] controls,output wire[104:0] bridge_sample);
reg clk=0;always #5 clk=~clk;
wire tx,pc_tx,owner,fault,stopped;wire[3:0] state;wire[31:0] accepted;wire[15:0] pan,tilt;wire[1:0] mask;
wire[31:0] status={accepted[15:0],7'b0,mask,stopped,fault,owner,state};
assign bridge_sample={32'b0,8'b0,32'b0,status,tx};
zynq_motion_s1 dut(clk,controls[0],controls[1],controls[2],controls[3],controls[4],controls[6:5],controls[22:7],controls[150:23],controls[151],controls[152],controls[153],mcu_rx,pc_tx,tx,owner,fault,stopped,state,accepted,pan,tilt,mask);
endmodule
