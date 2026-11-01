`timescale 1ns/1ps
module measurement_session_tb;
 reg clk=0;always #500 clk=~clk;
 reg rst=0,configure=0;reg[63:0] session=2;
 wire active,fault,valid;wire[63:0] bound;wire[7:0] data;
 reg send=0;reg[7:0] byte_in;wire ready,serial,busy,done;
 measurement_session #(.CLOCK_HZ(1000000),.BAUD(100000)) dut(clk,rst,configure,1'b1,64'd1,session,serial,1'b1,valid,data,active,fault,bound);
 uart_tx_8n1 #(.CLOCK_HZ(1000000),.BAUD(100000)) source(clk,rst,1'b0,send,byte_in,ready,serial,busy,done);
 function[7:0] hx;input[3:0] n;begin hx=n<10?48+n:87+n;end endfunction
 function[15:0] crcbyte;input[15:0] c;input[7:0] b;integer k;reg[15:0] v;
 begin v=c^{b,8'b0};for(k=0;k<8;k=k+1)v=v[15]?(v<<1)^16'h1021:v<<1;crcbyte=v;end endfunction
 task put;input[7:0] b;begin wait(ready);@(negedge clk);byte_in=b;send=1;@(negedge clk);send=0;wait(done);end endtask
 task ack;input[63:0] ns,ss;input bad;integer i;reg[7:0] b;reg[15:0] crc;
 begin crc=16'hffff;
 for(i=0;i<37;i=i+1)begin
 case(i)0:b="V";1:b="2";2:b="A";3,20:b=" ";default:b=i<20?hx(ns[63-(i-4)*4 -:4]):hx(ss[63-(i-21)*4 -:4]);endcase
 crc=crcbyte(crc,b);put(b);end
 put("*");if(bad)crc=crc^1;
 put(hx(crc[15:12]));put(hx(crc[11:8]));put(hx(crc[7:4]));put(hx(crc[3:0]));put(10);#5000;
 end endtask
 initial begin
 #3300;rst=1;@(negedge clk);configure=1;@(negedge clk);configure=0;#100000;
 put(10);if(active)$fatal(1,"LF accepted as ACK");
 ack(1,2,1);if(active)$fatal(1,"CRC error accepted");
 ack(2,2,0);if(active)$fatal(1,"wrong nonce accepted");
 ack(1,1,0);if(active)$fatal(1,"old session accepted");
 ack(1,2,0);if(!active||fault)$fatal(1,"valid ACK rejected");
 rst=0;#3000;rst=1;session=3;@(negedge clk);configure=1;@(negedge clk);configure=0;#100000;
 ack(1,2,0);if(active)$fatal(1,"pre-reset ACK accepted");
 #201000000;if(active||!fault)$fatal(1,"reply timeout failed closed");
 $display("C1_SESSION_PASS LF CRC nonce session correct_ACK reset replay timeout");$finish;
 end
 initial begin #300000000;$fatal(1,"session watchdog");end
endmodule
