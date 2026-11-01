`timescale 1ns/1ps
module vision_cdc_tb;
 reg sclk=0,dclk=0;always #7 sclk=~sclk;initial begin #0;forever #5 dclk=~dclk;end
 reg srst=0,drst=0,sv=0,dr=0;reg[218:0] sd=0;
 wire ready,dv;wire[218:0] dd;wire[31:0] dropped;
 integer sent=0,got=0,i,j;reg[218:0] expected[0:2047];
 vision_snapshot_cdc #(.WIDTH(219)) dut(sclk,dclk,srst,drst,sv,sd,ready,dropped,dv,dd,dr);
 always @(posedge sclk)if(srst&&drst&&sv&&ready)begin expected[sent]=sd;sent=sent+1;end
 always @(posedge dclk)if(srst&&drst&&dv&&dr)begin
  if(got>=sent||dd!==expected[got])$fatal(1,"torn/duplicate CDC payload");got=got+1;
 end
 reg[218:0] last_hold; reg was_busy=0;
 always @(negedge sclk) begin
  if(!srst||!drst) was_busy=0;
  else begin
   if(was_busy && dut.holding!==last_hold)$fatal(1,"payload changed while outstanding");
   last_hold=dut.holding;was_busy=!ready;
  end
 end
 initial begin
 #31;srst=1;#13;drst=1;
 for(i=0;i<2400;i=i+1)begin
  @(negedge sclk);sv=(i%3!=0);sd={7{i[31:0]^32'hfedcba98}};dr=(i%7>2);
 end
 @(negedge sclk);sv=0;dr=1;#1000;
 if(got!=sent||got<40||dropped==0)$fatal(1,"CDC stress did not drain or exercise drops");
 // A waiting snapshot must be flushed by either domain reset, no replay.
 for(j=0;j<2;j=j+1)begin
 dr=0;@(negedge sclk);sv=1;sd={219{1'b1}};@(negedge sclk);sv=0;#100;
 if(j==0)srst=0;else drst=0;
 #30;sent=0;got=0;srst=1;drst=1;dr=1;#150;
 if(dv||got!=0)$fatal(1,"stale snapshot after independent reset");
 @(negedge sclk);sv=1;sd={109{2'b10}};@(negedge sclk);sv=0;#200;
 if(got!=1)$fatal(1,"mailbox failed to recover explicitly");
 end
 $display("C1_CDC_PASS atomic_stress backpressure drops independent_reset recovery");$finish;
 end
 initial begin #100000;$fatal(1,"CDC watchdog");end
endmodule
