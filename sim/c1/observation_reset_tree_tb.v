`timescale 1ns/1ps
module observation_reset_tree_tb;
 reg sc=0,dc=0,sc_run=1,dc_run=1,rst=0;
 always #10 if(sc_run)sc=~sc;
 always #7 if(dc_run)dc=~dc;
 reg[7:0] controls=0;
 wire tx,pc_tx,owner,fault,stopped,active;wire[3:0] state;wire[31:0] dropped,mdropped;
 reset_cdc_audit_top dut(sc,dc,rst,controls,128'd1,64'd1,
  219'd0,1'b0,1'b1,tx,pc_tx,owner,fault,stopped,active,state,dropped,mdropped);
 realtime ls,ld;
 always @(posedge sc)ls=$realtime;
 always @(posedge dc)ld=$realtime;
 always @(posedge dut.c1_sys_release[1])
  if($realtime!=ls)$fatal(1,"system release not clock aligned");
 always @(posedge dut.c1_cam_release[1])
  if($realtime!=ld)$fatal(1,"camera release not clock aligned");
 // Sample after delta propagation, including initialization/reset assertions.
 always @(negedge sc)begin #0.01;if(tx!==1'b1)$fatal(1,"unsolicited UART output");end
 task check_idle;begin
  if(owner||fault||active||state!==0||tx!==1)$fatal(1,"reset restored control state");
 end endtask
 task check_assert;begin
  #0.1;if(dut.c1_sys_release!==0||dut.c1_cam_release!==0)
   $fatal(1,"common reset did not asynchronously assert");
  check_idle;
 end endtask
 integer i;
 initial begin
  #23;rst=1;#200;check_idle;
  // Global pulses shorter than either clock period must still flush the trees.
  #2;rst=0;check_assert;#1;rst=1;#200;check_idle;
  // Camera clock may stop: assertion still propagates, release must wait.
  @(negedge dc);dc_run=0;controls[0]=1;#60;check_assert;
  controls[0]=0;#100;if(dut.c1_cam_release!==0)$fatal(1,"camera released without clock");
  dc_run=1;#100;check_idle;
  // System stopped: global reset assertion works; neither domain releases early.
  @(negedge sc);sc_run=0;rst=0;check_assert;#1;rst=1;#100;
  if(dut.c1_sys_release!==0||dut.c1_cam_release!==0)$fatal(1,"release without system clock");
  sc_run=1;#200;check_idle;
  for(i=0;i<20;i=i+1)begin
   #3;controls[0]=1;#60;check_assert;controls[0]=0;#200;check_idle;
  end
  $display("OBSERVATION_RESET_TREE_PASS 24");$finish;
 end
 initial begin #15000;$fatal(1,"watchdog");end
endmodule
