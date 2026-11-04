`timescale 1ns/1ps
module c1_axis_step_gate_tb;
 reg clk=0,reset_n=0,ready=0,step=0,center=0;
 wire command,rejected;wire [1:0] axis;wire [15:0] pulse_us;
 wire command0,rejected0;wire [1:0] axis0;wire [15:0] pulse0;
 always #5 clk=~clk;
 c1_axis_step_gate #(.AXIS(1)) dut(clk,reset_n,ready,step,center,command,axis,pulse_us,rejected);
 c1_axis_step_gate #(.AXIS(0)) dut0(clk,reset_n,ready,step,center,command0,axis0,pulse0,rejected0);
 task tick;begin @(posedge clk);#1;end endtask
 task fail;input [255:0] why;begin $display("FAIL %s",why);$fatal(1);end endtask
 initial begin
  tick;if(command)fail("reset transmits");reset_n=1;tick;
  step=1;tick;if(!rejected||command||!rejected0||command0)fail("busy accepts");
  ready=1;tick;if(command)fail("held input repeats");step=0;tick;
  step=1;tick;if(!command||axis!=1||pulse_us!=1550||!command0||axis0!=0||pulse0!=1550)fail("step");
  tick;if(command)fail("held step repeats");step=0;tick;
  center=1;tick;if(!command||axis!=1||pulse_us!=1500||!command0||axis0!=0||pulse0!=1500)fail("center");
  center=0;tick;step=1;center=1;tick;if(!rejected||command)fail("simultaneous");
  reset_n=0;tick;if(command)fail("reset command");
  ready=1;step=1;center=0;reset_n=1;tick;if(command)fail("held across reset");
  step=0;tick;step=1;tick;if(!command)fail("rearmed after release");
  $display("PASS c1 axis gate; STM32 may enable both channels");$finish;
 end
 initial begin #10000;fail("timeout");end
endmodule
