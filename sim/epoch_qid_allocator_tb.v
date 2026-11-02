`timescale 1ns/1ps
module epoch_qid_allocator_tb;
 reg clk=0,reset_n=0,load=0,take=0,stop_take=0;
 reg [127:0] first=0,last=0;
 wire [127:0] qid;wire valid,denied,active,fault,stop_only;
 integer checks=0,failures=0;
 always #5 clk=~clk;
 epoch_qid_allocator dut(clk,reset_n,load,first,last,take,stop_take,
 qid,valid,denied,active,fault,stop_only);
 task check;input condition;input [8*60-1:0] name;begin
  checks=checks+1;
  if(condition!==1'b1) begin failures=failures+1;$display("FAIL %0s",name);end
 end endtask
 task tick;begin @(posedge clk);#1;end endtask
 task reset;begin @(negedge clk);reset_n=0;load=0;take=0;stop_take=0;tick;
  check(!active&&!fault&&!valid&&qid==0,"reset clears volatile grant and result");
  @(negedge clk);reset_n=1;tick;end endtask
 task grant;input [127:0] a,b;begin
  @(negedge clk);first=a;last=b;load=1;tick;
  @(negedge clk);load=0;tick;end endtask
 task normal;input [127:0] expected;begin
  @(negedge clk);take=1;tick;check(valid&&qid==expected,"normal ID exact and monotonic");
  @(negedge clk);take=0;tick;check(!valid,"valid pulse ends");end endtask
 initial begin
  reset;
  @(negedge clk);take=1;tick;check(denied&&!valid&&!active,"no grant no QID");
  @(negedge clk);take=0;
  grant(128'd100,128'd102);check(active&&!fault,"load bounded interval");
  normal(100);normal(101);check(stop_only,"last ID reserved for STOP");
  @(negedge clk);take=1;tick;check(denied&&!valid&&active,"normal refused without consuming STOP ID");
  @(negedge clk);take=0;stop_take=1;tick;
  check(valid&&qid==102&&!active,"STOP uses final ID then invalidates grant");
  @(negedge clk);stop_take=0;tick;
  grant(100,102);check(fault&&!active,"same-boot replayed range faults");
  grant(200,202);check(fault&&!active,"fault locked until reset");
  reset;grant(200,210);normal(200);
  @(negedge clk);stop_take=1;tick;check(valid&&qid==201&&!active,"early STOP burns unused suffix");
  @(negedge clk);stop_take=0;tick;grant(211,213);normal(211);
  grant(220,230);check(fault&&!active,"overwrite active lease faults");
  reset;grant(0,3);check(fault&&!active,"zero range rejected");
  reset;grant(10,9);check(fault&&!active,"backward range rejected");
  reset;grant(10,20);
  @(negedge clk);take=1;stop_take=1;tick;check(fault&&!valid&&!active,"ambiguous allocation faults");
  reset;grant({128{1'b1}}-1'b1,{128{1'b1}});normal({128{1'b1}}-1'b1);
  @(negedge clk);stop_take=1;tick;check(valid&&qid=={128{1'b1}}&&!active,"maximum STOP no wrap");
  @(negedge clk);stop_take=0;tick;check(!valid&&!active,"exhausted grant remains inactive");
  reset;grant(50,60);normal(50);reset;check(!active,"reset never restores authorization or grant");
  // Deliberate limitation: provider replay across reset is NOT detectable here.
  grant(50,60);normal(50);
  $display("LIMITATION volatile guard accepts replayed provider grant after reset; trusted provider required");
  if(failures==0)$display("PASS epoch_qid_allocator checks=%0d failures=0",checks);
  else $display("FAIL epoch_qid_allocator checks=%0d failures=%0d",checks,failures);
  $finish;
 end
 initial begin #20000;$display("FAIL watchdog");$finish;end
endmodule
