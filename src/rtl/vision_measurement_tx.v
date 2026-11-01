`timescale 1ns/1ps
// Camera-domain result must arrive atomically in clk domain via a reviewed CDC.
// Byte-stream candidate only: no pins, no private UART driver, no motion opcode.
// control_pending inhibits NEW measurement lines; accepted lines finish intact.
module vision_measurement_tx(
 input wire clk,input wire rst_n,input wire capture,input wire control_pending,
 input wire [7:0] camera_id,input wire [7:0] mask_version,
 input wire [63:0] session_id,input wire [31:0] frame_seq,input wire [31:0] capture_tick,
 input wire timestamp_valid,input wire complete,input wire target,
 input wire [15:0] width,input wire [15:0] height,
 input wire [18:0] count,input wire [27:0] sum_x,input wire [27:0] sum_y,
 input wire [9:0] xmin,input wire [8:0] ymin,input wire [9:0] xmax,input wire [8:0] ymax,
 output reg [7:0] data,output wire valid,input wire ready,
 output wire busy,output reg done,output reg [31:0] dropped
);
 reg [431:0] packet;
 reg [6:0] pos;reg active;reg [15:0] crc;reg[5:0] crc_pos;reg preparing;
 wire good=complete&&target&&(count!=0);
 wire [15:0] cx=good?sum_x/count:16'd0;
 wire [15:0] cy=good?sum_y/count:16'd0;
 function [15:0] crcbyte;input[15:0] c;input[7:0] b;integer i;reg[15:0] v;
 begin v=c^{b,8'b0};for(i=0;i<8;i=i+1)v=v[15]?(v<<1)^16'h1021:v<<1;crcbyte=v;end endfunction
 function[7:0] hexchar;input[3:0] v;begin hexchar=v<10?8'd48+v:8'd87+v;end endfunction
 assign valid=active&&!preparing;assign busy=active;
 always @* begin
  data=0;
  if(pos==0)data="v";else if(pos==1)data="2";else if(pos==2)data=" ";
  else if(pos==111)data=10;
  else if(pos>=3&&pos<111)data=hexchar(packet[431-(pos-3)*4 -:4]);
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin packet<=0;pos<=0;active<=0;preparing<=0;crc<=16'hffff;crc_pos<=0;done<=0;dropped<=0;end
  else begin
   done<=0;
   if(capture)begin
    if(active||control_pending||session_id==0)dropped<=dropped+1;
    else begin
     packet<={16'ha55a,8'd2,8'd1,camera_id,{5'b0,timestamp_valid,good,complete},8'd1,mask_version,
       session_id,frame_seq,(timestamp_valid?capture_tick:32'd0),width,height,
       (good?{13'b0,count}:32'd0),(good?{4'b0,sum_x}:32'd0),(good?{4'b0,sum_y}:32'd0),
       (good?{6'b0,xmin}:16'd0),(good?{7'b0,ymin}:16'd0),(good?{6'b0,xmax}:16'd0),(good?{7'b0,ymax}:16'd0),cx,cy,16'd0};
     pos<=0;active<=1;preparing<=1;crc<=16'hffff;crc_pos<=0;
    end
   end
   if(preparing)begin
    crc<=crcbyte(crc,packet[431-crc_pos*8 -:8]);
    if(crc_pos==51)begin packet[15:0]<=crcbyte(crc,packet[23:16]);preparing<=0;end
    else crc_pos<=crc_pos+1;
   end else if(valid&&ready)begin
    if(pos==111)begin active<=0;done<=1;end else pos<=pos+1;
   end
  end
 end
endmodule
