`timescale 1ns/1ps
module two_axis_step_gate_v2_tb;
 reg clk=0,reset_n=0,ready=0,step=0,center=0;
 reg[1:0] axis_select=0;
 wire command,rejected;wire[1:0] axis;wire[15:0] pulse_us;
 integer checks=0;
 always #5 clk=~clk;
 c1_two_axis_step_gate_v2 dut(clk,reset_n,ready,axis_select,step,center,
                              command,rejected,axis,pulse_us);
 task sample;
 input[1:0] sel;input st,ce,rdy,expected_command,expected_reject;
 input[1:0] expected_axis;input[15:0] expected_pulse;
 begin
  @(negedge clk);axis_select=sel;step=st;center=ce;ready=rdy;#1;
  if(command!==expected_command || (expected_command && (axis!==expected_axis||pulse_us!==expected_pulse)))
   begin $display("FAIL combinational command");$fatal(1);end
  @(posedge clk);#1;
  if(rejected!==expected_reject)begin $display("FAIL rejection");$fatal(1);end
  checks=checks+1;
 end endtask
 initial begin
  step=1;repeat(2) @(negedge clk);reset_n=1;
  sample(0,1,0,1,0,0,0,0);sample(0,0,0,1,0,0,0,0);
  sample(0,1,0,0,0,1,0,0);sample(0,0,0,1,0,0,0,0);
  sample(0,1,0,1,1,0,0,1550);sample(1,1,0,1,0,0,0,0);
  sample(1,0,0,1,0,0,0,0);sample(1,1,0,1,1,0,1,1550);
  sample(1,0,0,1,0,0,0,0);sample(1,0,1,1,1,0,1,1500);
  sample(1,0,0,1,0,0,0,0);sample(0,0,1,1,1,0,0,1500);
  sample(0,0,0,1,0,0,0,0);sample(2,1,0,1,0,1,0,0);
  sample(0,0,0,1,0,0,0,0);sample(0,1,1,1,0,1,0,0);
  sample(0,1,1,1,0,0,0,0);sample(0,0,0,1,0,0,0,0);
  $display("TWO_AXIS_V2_PASS checks=%0d",checks);$finish;
 end
 initial begin #5000;$display("FAIL timeout");$fatal(1);end
endmodule
