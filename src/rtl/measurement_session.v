`timescale 1ns/1ps
// Explicit observation configuration bus, not an arm/nonce-generation mechanism.
// nonce is supplied from a reviewed MCU status/configuration source. CRC is not authentication.
module measurement_session #(parameter CLOCK_HZ=100000000,BAUD=115200)(
 input wire clk,reset_n,configure,allowed,input wire[63:0] nonce,session,
 input wire mcu_rx,input wire ready,output wire valid,output wire[7:0] data,
 output reg active,output reg fault,output reg[63:0] bound_session
);
 reg old_config,busy;integer pos,age,rxpos;reg[63:0] saved_nonce;
 reg[15:0] txcrc,rxcrc,received_crc;reg match;
 wire[7:0] rd;wire rv,re,rb;
 uart_rx #(.CLOCK_HZ(CLOCK_HZ),.BAUD(BAUD)) rx(clk,reset_n,mcu_rx,rd,rv,re,rb);
 function[7:0] hx;input[3:0] n;begin hx=n<10?48+n:87+n;end endfunction
 function[15:0] crcbyte;input[15:0] c;input[7:0] b;integer i;reg[15:0] v;
 begin v=c^{b,8'b0};for(i=0;i<8;i=i+1)v=v[15]?(v<<1)^16'h1021:v<<1;crcbyte=v;end endfunction
 function[7:0] body;input integer p;input reply;
 begin
 case(p)0:body=reply?"V":"v";1:body="2";2:body=reply?"A":"b";3,20:body=" ";
 default:if(p<20)body=hx(saved_nonce[63-(p-4)*4 -:4]);else body=hx(bound_session[63-(p-21)*4 -:4]);endcase
 end endfunction
 function[4:0] uh;input[7:0] b;begin uh=b>=48&&b<=57?b-48:b>=97&&b<=102?b-87:16;end endfunction
 assign valid=busy&&pos<43;
 assign data=pos<37?body(pos,0):pos==37?"*":pos==42?10:hx(txcrc[15-(pos-38)*4 -:4]);
 always @(posedge clk or negedge reset_n)begin
 if(!reset_n)begin old_config<=0;busy<=0;pos<=0;age<=0;active<=0;fault<=0;bound_session<=0;saved_nonce<=0;txcrc<=16'hffff;rxpos<=0;rxcrc<=16'hffff;received_crc<=0;match<=1;end
 else begin
 old_config<=configure;
 if(configure&&!old_config&&allowed&&!busy&&nonce!=0&&session!=0)begin
  busy<=1;active<=0;fault<=0;pos<=0;age<=0;saved_nonce<=nonce;bound_session<=session;txcrc<=16'hffff;
  rxpos<=0;rxcrc<=16'hffff;received_crc<=0;match<=1;
 end
 if(busy)begin
  age<=age+1;if(age>=CLOCK_HZ/5)begin busy<=0;active<=0;fault<=1;end
  if(valid&&ready)begin pos<=pos+1;if(pos<37)txcrc<=crcbyte(txcrc,data);end
 end
 if(re&&busy)begin busy<=0;active<=0;fault<=1;end
 if(rv)begin
  if(rd==10)begin
   if(busy&&pos==43&&rxpos==42&&match&&rxcrc==received_crc)begin busy<=0;active<=1;fault<=0;end
   rxpos<=0;rxcrc<=16'hffff;received_crc<=0;match<=1;
  end else begin
   if(rxpos<255)rxpos<=rxpos+1;else match<=0;
   if(rxpos<37)begin rxcrc<=crcbyte(rxcrc,rd);if(rd!=body(rxpos,1))match<=0;end
   else if(rxpos==37)begin if(rd!="*")match<=0;end
   else if(rxpos<42)begin received_crc<=(received_crc<<4)|uh(rd);if(uh(rd)>15)match<=0;end
   else match<=0;
  end
 end
 end end
endmodule
