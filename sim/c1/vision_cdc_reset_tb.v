`timescale 1ns/1ps
module vision_cdc_reset_tb;
 reg sc=0,dc=0,sc_run=1,dc_run=1;always #7 if(sc_run)sc=~sc;always #5 if(dc_run)dc=~dc;
 reg sr=0,dr=0,valid=0,ready=0;reg[218:0] data=0;
 wire space,got;wire[218:0] value;wire[31:0] dropped;
 vision_snapshot_cdc #(.WIDTH(219)) dut(sc,dc,sr,dr,valid,data,space,dropped,got,value,ready);
 realtime last_s,last_d;
 always @(posedge sc)last_s=$realtime;
 always @(posedge dc)last_d=$realtime;
 always @(posedge dut.src_run_n)if($realtime!=last_s)$fatal(1,"source release off clock edge");
 always @(posedge dut.dst_run_n)if($realtime!=last_d)$fatal(1,"destination release off clock edge");
 task flush_check;begin #0.1;if(space||got||value!==0||dropped!==0)$fatal(1,"reset did not flush immediately");end endtask
 task send;input[218:0] x;begin wait(space);@(negedge sc);data=x;valid=1;@(negedge sc);valid=0;end endtask
 integer i;
 initial begin
 #13;sr=1;#9;dr=1;wait(space);send({219{1'b1}});wait(got);if(value!=={219{1'b1}})$fatal(1,"initial transfer");
 // A sub-cycle pulse from either side must invalidate the blocked destination.
 #2;sr=0;flush_check;#1;sr=1;#150;if(got)$fatal(1,"stale payload resurrected");
 send({109{2'b10}});wait(got);#1;dr=0;flush_check;#1;dr=1;#150;if(got)$fatal(1,"destination reset replay");
 // Release with destination clock stopped: no local release until clock returns.
 @(negedge dc);dc_run=0;sr=0;flush_check;#2;sr=1;#100;
 if(dut.dst_run_n||got)$fatal(1,"release without destination clock");
 send(219'h123456);#100;if(got)$fatal(1,"delivery without destination clock");
 dc_run=1;wait(got);if(value!==219'h123456)$fatal(1,"paused-clock transfer lost");
 ready=1;#100;
 // Alternating short independent resets at different clock phases.
 for(i=0;i<20;i=i+1)begin
  #3;if(i%2)sr=0;else dr=0;flush_check;#1;sr=1;dr=1;#100;
  if(got)$fatal(1,"reset traffic manufactured a payload");
 end
 $display("CDC_RESET_BOUNDARY_PASS 26");$finish;
 end
 initial begin #10000;$fatal(1,"watchdog");end
endmodule
