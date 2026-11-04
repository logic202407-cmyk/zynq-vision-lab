`timescale 1ns/1ps
module motion_epoch_guard_tb;
 reg clk=0,reset_n=0,query=0;
 reg [127:0] epoch=0;
 wire owner,fault,stopped,pc_tx,mcu_tx;
 wire [3:0] state; wire [31:0] count; wire [15:0] pan,tilt; wire [1:0] pwm;
 always #500 clk=~clk;
 zynq_motion_s1 #(.CLOCK_HZ(1000000),.BAUD(100000),.TX_MS(50)) dut(
 .clk(clk),.reset_n(reset_n),.query(query),.authorize(1'b0),.command(1'b0),
 .stop_request(1'b0),.axis(2'b0),.pulse_us(16'd0),.epoch(epoch),
 .request_local(1'b1),.pc_quiet_ack(1'b1),.pc_rx(1'b1),.mcu_rx(1'b1),
 .pc_tx(pc_tx),.mcu_tx(mcu_tx),.owner(owner),.fault(fault),.stop_confirmed(stopped),
 .state(state),.accepted_count(count),.pan_target(pan),.tilt_target(tilt),.pwm_mask(pwm));
 task issue; input [127:0] id; begin
  @(negedge clk);epoch=id;query=1;@(negedge clk);query=0;repeat(3) @(negedge clk);
 end endtask
 task check_idle; begin if(state!==0 || !mcu_tx || pwm!==0) begin $display("FAIL rejected QID");$fatal(1);end end endtask
 initial begin
  repeat(3) @(negedge clk);reset_n=1;wait(owner);@(negedge clk);
  // White-box fixture models a previously issued high-water mark, rather
  // than claiming that a prior transaction has been exercised in this TB.
  dut.last_epoch=128'd100;
  issue(0);check_idle;issue(50);check_idle;issue(100);check_idle;
  issue(101);if(state!==1 || dut.qid!==101) begin $display("FAIL newer QID");$fatal(1);end
  @(negedge clk);reset_n=0;repeat(3) @(negedge clk);reset_n=1;wait(owner);@(negedge clk);
  issue(50);if(state!==1 || dut.qid!==50) begin $display("FAIL expected reset limitation");$fatal(1);end
  $display("PASS same-boot monotonic guard; LIMITATION replay accepted after reset");$finish;
 end
 initial begin #5000000;$display("FAIL timeout");$fatal(1);end
endmodule
