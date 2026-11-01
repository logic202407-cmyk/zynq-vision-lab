`timescale 1ns/1ps
// Two line banks: a STOP can arrive while the preceding control line drains.
// Does not forward partial commands; a third outstanding line fails closed.
module uart_line_queue #(parameter CLOCK_HZ=100000000,BAUD=115200,MAX_BYTES=64)(
 input wire clk,reset_n,serial_in,
 output wire valid,output wire[7:0] data,input wire ready,
 output reg fault,output wire pending
);
 wire[7:0] rd;wire rv,re,rb;reg[7:0] mem[0:2*MAX_BYTES-1];
 integer wr,at,age;reg[1:0] full;reg write_bank,read_bank;
 uart_rx #(.CLOCK_HZ(CLOCK_HZ),.BAUD(BAUD)) rx(clk,reset_n,serial_in,rd,rv,re,rb);
 assign valid=full[read_bank]&&!fault;assign data=mem[read_bank*MAX_BYTES+at];assign pending=(|full)||wr!=0||rb;
 always @(posedge clk or negedge reset_n)begin
  if(!reset_n)begin wr<=0;at<=0;full<=0;write_bank<=0;read_bank<=0;age<=0;fault<=0;end
  else begin
   if(wr!=0)begin age<=age+1;if(age>=CLOCK_HZ/50)fault<=1;end else age<=0;
   if(re)fault<=1;
   if(rv)begin
    if(full[write_bank]||wr>=MAX_BYTES)fault<=1;
    else begin mem[write_bank*MAX_BYTES+wr]<=rd;wr<=wr+1;
     if(rd==10)begin full[write_bank]<=1;wr<=0;write_bank<=!write_bank;end
    end
   end
   if(valid&&ready)if(data==10)begin full[read_bank]<=0;at<=0;read_bank<=!read_bank;end else at<=at+1;
  end
 end
endmodule
