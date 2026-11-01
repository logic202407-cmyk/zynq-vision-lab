`timescale 1ns/1ps
module measurement_divider_tb;
 reg clk=0;always #5 clk=~clk;reg rst=0,cap=0;reg[18:0] count;
 reg[27:0] sx,sy;wire[7:0] data;wire valid,busy,done;wire[31:0] drop;
 reg[7:0] bytes[0:53];reg[3:0] high;integer i,pos=0,k;reg[15:0] crc;
 function[3:0] uh;input[7:0] b;begin uh=b<=57?b-48:b-87;end endfunction
 function[15:0] crcbyte;input[15:0] c;input[7:0] b;integer n;reg[15:0] v;
 begin v=c^{b,8'b0};for(n=0;n<8;n=n+1)v=v[15]?(v<<1)^16'h1021:v<<1;crcbyte=v;end endfunction
 vision_measurement_tx dut(clk,rst,cap,1'b0,8'd0,8'd1,64'd1,32'd1,32'd0,1'b0,1'b1,1'b1,
 16'd640,16'd480,count,sx,sy,10'd0,9'd0,10'd639,9'd479,data,valid,1'b1,busy,done,drop);
 always @(posedge clk)if(valid)begin
 if(pos>=3&&pos<111)begin
 if((pos-3)%2==0)high=uh(data);else bytes[(pos-3)/2]={high,uh(data)};
 end
 pos=pos+1;
 end
 initial begin
 #33;rst=1;
 for(i=1;i<=64;i=i+1)begin
  @(negedge clk);count=i==64?307200:i*47+1;sx=count*(i*9%639)+(i%count);sy=count*(i*7%479)+(i%count);pos=0;cap=1;
  @(negedge clk);cap=0;wait(done);@(negedge clk);
  if(pos!=112||{bytes[48],bytes[49]}!==sx/count||{bytes[50],bytes[51]}!==sy/count)$fatal(1,"iterative centroid mismatch case=%0d",i);
  crc=16'hffff;for(k=0;k<52;k=k+1)crc=crcbyte(crc,bytes[k]);
  if(crc!=={bytes[52],bytes[53]})$fatal(1,"CRC after divider");
 end
 $display("C1_DIVIDER_PASS 64 floor_division_and_CRC_vectors");$finish;
 end
 initial begin #1000000;$fatal(1,"divider watchdog");end
endmodule
