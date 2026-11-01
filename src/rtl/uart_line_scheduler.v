`timescale 1ns/1ps
// One serializer, non-preemptive complete lines. Priority control > config > vision.
// Upstream sources must keep valid/data until ready and terminate each line with LF.
module uart_line_scheduler #(parameter CLOCK_HZ=100000000,BAUD=115200)(
 input wire clk,reset_n,enable,control_pending,
 input wire cv,input wire[7:0] cd,output wire cr,
 input wire bv,input wire[7:0] bd,output wire br,
 input wire vv,input wire[7:0] vd,output wire vr,
 output wire tx,output reg fault,output wire idle
);
 reg[1:0] owner;reg waiting,last;integer age,length;
 wire ready,busy,done;wire valid=owner==1?cv:owner==2?bv:owner==3?vv:1'b0;
 wire[7:0] data=owner==1?cd:owner==2?bd:vd;
 wire accept=ready&&!waiting&&!fault&&owner!=0;
 assign cr=accept&&owner==1;assign br=accept&&owner==2;assign vr=accept&&owner==3;
 assign idle=owner==0&&!busy;
 uart_tx_8n1 #(.CLOCK_HZ(CLOCK_HZ),.BAUD(BAUD)) serializer(clk,reset_n,1'b0,valid&&accept,data,ready,tx,busy,done);
 always @(posedge clk or negedge reset_n)begin
  if(!reset_n)begin owner<=0;waiting<=0;last<=0;age<=0;length<=0;fault<=0;end
  else begin
   if(owner==0)begin
    age<=0;length<=0;
    if(enable&&!fault)if(cv)owner<=1;else if(!control_pending&&bv)owner<=2;else if(!control_pending&&!bv&&vv)owner<=3;
   end else begin
    age<=age+1;if(age>=CLOCK_HZ/50)fault<=1; // 20ms line deadline, no retry.
    if(valid&&accept)begin waiting<=1;last<=data==10;length<=length+1;if(length>=127)fault<=1;end
    if(waiting&&done)begin waiting<=0;if(last)owner<=0;end
    if(fault&&!busy)begin owner<=0;waiting<=0;end
   end
  end
 end
endmodule
