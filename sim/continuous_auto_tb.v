`timescale 1ns/1ps
// Boundary tests seed an already acknowledged AUTO state; no physical devices.
module continuous_auto_tb;
 integer logfd;
 reg clk=0; always #5 clk=~clk;
 reg reset_n=0,stop=0,local_owner=1;
 zynq_motion_s1 #(.CLOCK_HZ(1000000),.BAUD(100000),.ALLOW_AUTO(1),.CONTINUOUS_AUTO(1)) dut(
 .clk(clk),.reset_n(reset_n),.query(1'b0),.authorize(1'b0),.command(1'b0),.stop_request(stop),
 .axis(2'b11),.pulse_us(16'd0),.epoch(128'd1),.request_local(local_owner),.pc_quiet_ack(1'b1),.pc_rx(1'b1),.mcu_rx(1'b1));
 zynq_motion_s1 #(.CLOCK_HZ(1000000),.BAUD(100000),.ALLOW_AUTO(1)) legacy(
 .clk(clk),.reset_n(reset_n),.query(1'b0),.authorize(1'b0),.command(1'b0),.stop_request(1'b0),
 .axis(2'b11),.pulse_us(16'd0),.epoch(128'd1),.request_local(1'b1),.pc_quiet_ack(1'b1),.pc_rx(1'b1),.mcu_rx(1'b1));
 task seed;
 begin
 reset_n=0;stop=0;local_owner=1;repeat(3)@(negedge clk);reset_n=1;@(negedge clk);
 dut.owner=1;dut.authorized=1;dut.auto_mode=1;dut.state=4;dut.stop_confirmed=0;
 dut.now_ms=30001;dut.auth_at=0;dut.live_at=30001;
 legacy.owner=1;legacy.authorized=1;legacy.auto_mode=1;legacy.state=4;legacy.stop_confirmed=0;
 legacy.now_ms=30001;legacy.auth_at=0;legacy.live_at=30001;
 end endtask
 initial begin
 logfd=$fopen("boundary-results.log","w");
 seed;@(negedge clk);
 if(!dut.authorized||dut.cancel_pending)$fatal(1,"continuous AUTO expired");
 if(legacy.authorized||!legacy.cancel_pending)$fatal(1,"default bounded AUTO changed");
 $fdisplay(logfd,"PASS opt-in continues beyond 30s; default expires");
 seed;dut.auto_mode=0;@(negedge clk);
 if(dut.authorized||!dut.cancel_pending)$fatal(1,"pre-AUTO authorization must expire");
 $fdisplay(logfd,"PASS ARM without AUTO remains bounded");
 seed;stop=1;@(negedge clk);
 if(dut.authorized||!dut.cancel_pending)$fatal(1,"STOP failed");
 $fdisplay(logfd,"PASS STOP revokes continuous mode");
 seed;local_owner=0;@(negedge clk);
 if(dut.authorized||!dut.cancel_pending)$fatal(1,"owner release failed");
 $fdisplay(logfd,"PASS owner release revokes continuous mode");
 seed;dut.state=5;dut.op=5;dut.deadline=29800;@(negedge clk);
 if(!dut.fault||dut.authorized||!dut.cancel_pending)$fatal(1,"missing heartbeat ACK failed");
 $fdisplay(logfd,"PASS missing heartbeat ACK faults and stops");
 seed;reset_n=0;repeat(2)@(negedge clk);reset_n=1;repeat(5)@(negedge clk);
 if(dut.authorized||dut.auto_mode||dut.pwm_mask)$fatal(1,"reset resumed AUTO");
 $fdisplay(logfd,"PASS reset never resumes AUTO");
 $fdisplay(logfd,"CONTINUOUS_AUTO_PASS");$fclose(logfd);$finish;
 end
endmodule
