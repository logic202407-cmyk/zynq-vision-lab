`timescale 1ns/1ps
// Read-only S1SYNC observation. B2 separately validates the full safety response.
// Exact query epoch + CAP + prefix + whole-line CRC; periodic status is not a nonce ACK.
module measurement_nonce_observer #(parameter CLOCK_HZ=100000000,BAUD=115200)(
 input wire clk,reset_n,query_start,invalidate,input wire[127:0] epoch,input wire mcu_rx,
 output reg valid,output reg[63:0] nonce
);
 wire[7:0] rd;wire rv,re,rb;reg[127:0] expected_epoch;
 reg[63:0] candidate;reg[15:0] crc,received;reg match,star;integer pos,hexcount;
 uart_rx #(.CLOCK_HZ(CLOCK_HZ),.BAUD(BAUD)) rx(clk,reset_n,mcu_rx,rd,rv,re,rb);
 function[7:0] hx;input[3:0] n;begin hx=n<10?48+n:87+n;end endfunction
 function[4:0] uh;input[7:0] b;begin uh=b>=48&&b<=57?b-48:b>=97&&b<=102?b-87:16;end endfunction
 function[15:0] crcbyte;input[15:0] c;input[7:0] b;integer k;reg[15:0] v;
 begin v=c^{b,8'b0};for(k=0;k<8;k=k+1)v=v[15]?(v<<1)^16'h1021:v<<1;crcbyte=v;end endfunction
 function[7:0] prefix;input integer p;
 begin case(p)
 0:prefix="S";1:prefix="1";2:prefix="S";3:prefix="Y";4:prefix="N";5:prefix="C";
 6,39,46:prefix=" ";40:prefix="S";41:prefix="1";42:prefix="A";43:prefix="C";44:prefix="K";45:prefix="1";
 default:prefix=hx(expected_epoch[127-(p-7)*4 -:4]);endcase end endfunction
 always @(posedge clk or negedge reset_n)begin
 if(!reset_n)begin valid<=0;nonce<=0;expected_epoch<=0;candidate<=0;crc<=16'hffff;received<=0;match<=1;star<=0;pos<=0;hexcount<=0;end
 else begin
 if(invalidate||re)valid<=0;
 if(re)match<=0;
 if(query_start)begin expected_epoch<=epoch;valid<=0;end
 if(rv)begin
  if(rd==10)begin
   if(!invalidate&&match&&star&&hexcount==4&&crc==received&&pos>=64&&candidate!=0&&expected_epoch!=0)begin valid<=1;nonce<=candidate;end
   pos<=0;hexcount<=0;crc<=16'hffff;received<=0;match<=1;star<=0;candidate<=0;
  end else if(rd!=13)begin
   if(pos<255)pos<=pos+1;else match<=0;
   if(star)begin received<=(received<<4)|uh(rd);hexcount<=hexcount+1;if(uh(rd)>15||hexcount>=4)match<=0;end
   else if(rd==42)star<=1;
   else begin
    crc<=crcbyte(crc,rd);
    if(pos<47&&rd!=prefix(pos))match<=0;
    if(pos>=47&&pos<=62)begin candidate<=(candidate<<4)|uh(rd);if(uh(rd)>15)match<=0;end
    if(pos==63&&rd!=" ")match<=0;
   end
  end
 end
 end end
endmodule
