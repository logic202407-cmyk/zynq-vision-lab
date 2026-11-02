`timescale 1ns/1ps
// Interface-only test against a PRIVATE, hash-checked driver; no vendor source here.
module sccb_divider_tb;
 reg clk=0,rst_n=0;always #10 clk=~clk;
 wire drive,scl,done,ack;wire[7:0] received;tri1 sda;
 i2c_dri #(.CLK_FREQ(50000000),.I2C_FREQ(250000)) dut(
 .clk(clk),.rst_n(rst_n),.i2c_exec(1'b0),.bit_ctrl(1'b0),.i2c_rh_wl(1'b0),
 .i2c_addr(16'd0),.i2c_data_w(8'd0),.i2c_data_r(received),.i2c_done(done),
 .i2c_ack(ack),.scl(scl),.sda(sda),.dri_clk(drive));
 integer edges=0,transitions=0;reg previous=0;time rise_at=0;
 // Count actual active parent edges, then sample after the DUT's NBA update.
 // A falling-edge counter would invent a cycle if reset releases mid-low phase.
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin edges=0;previous=0;rise_at=0;end
  else begin
   #0.001;edges=edges+1;
   if(drive!==previous)begin
    if(edges!=25)$fatal(1,"divider half-period mismatch: %d",edges);
    if(drive)begin
     if(rise_at!=0 && $time-rise_at!=1000)$fatal(1,"generated period mismatch");
     rise_at=$time;
    end
    transitions=transitions+1;edges=0;previous=drive;
   end
  end
 end
 initial begin
  #47;rst_n=1;#20002;rst_n=0;#0.1;
  if(drive!==0)$fatal(1,"divider reset did not clear");
  #3;rst_n=1;#20000;
  if(transitions<78)$fatal(1,"insufficient observed transitions");
  $display("SCCB_DIVIDER_PASS transitions=%0d period_ns=1000 half_cycles=25",transitions);
  $finish;
 end
 initial begin #50000;$fatal(1,"watchdog");end
endmodule
