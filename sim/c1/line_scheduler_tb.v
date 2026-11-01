`timescale 1ns/1ps
module line_scheduler_tb;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,enable=1,urgent=0,cv=0,bv=0,vv=0;reg[7:0] cd="c",bd="b",vd="v";
 wire cr,br,vr,tx,fault,idle;integer cpos=0,bpos=0,vpos=0,n=0;reg[7:0] expected[0:8];
 wire[7:0] rd;wire rv,re,rb;
 uart_line_scheduler #(.CLOCK_HZ(1000000),.BAUD(100000)) dut(clk,rst,enable,urgent,cv,cd,cr,bv,bd,br,vv,vd,vr,tx,fault,idle);
 uart_rx #(.CLOCK_HZ(1000000),.BAUD(100000)) rx(clk,rst,tx,rd,rv,re,rb);
 always @(posedge clk)begin
 if(re)$fatal(1,"bad stop bit");
 if(rv)begin if(n>=9||rd!==expected[n])$fatal(1,"interleaved/wrong priority n=%0d data=%h",n,rd);n=n+1;end
 if(vv&&vr)begin vpos<=vpos+1;if(vpos<2)vd<="x";else if(vpos==2)vd<=10;else vv<=0;end
 if(cv&&cr)begin if(cpos==0)begin cd<=10;cpos<=1;end else cv<=0;end
 if(bv&&br)begin if(bpos==0)begin bd<=10;bpos<=1;end else bv<=0;end
 end
 initial begin
 expected[0]="v";expected[1]="x";expected[2]="x";expected[3]=10;
 expected[4]="c";expected[5]=10;expected[6]="b";expected[7]=10;
 expected[8]="b"; // Last complete byte before the deliberately stalled source.
 #31;rst=1;@(negedge clk);vv=1;#500;cv=1;bv=1;urgent=1;
 wait(cpos==1);wait(!cv);urgent=0;wait(n==8);#200;
 if(!idle||fault)$fatal(1,"did not drain");
 // Start a line then withdraw valid. Bounded stall locks output after current byte.
 bv=1;bd="b";bpos=1;#100;bv=0;#210000;
 if(!fault||!tx)$fatal(1,"stall did not lock at idle high");
 rst=0;#30;if(!tx)$fatal(1,"reset TX not high");
 $display("C1_SCHEDULER_PASS whole_lines control_priority single_TX stall_lock reset_high");$finish;
 end
 initial begin #500000;$fatal(1,"scheduler watchdog");end
endmodule
