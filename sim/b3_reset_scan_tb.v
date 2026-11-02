`timescale 1ns/1ps
module b3_reset_scan_tb;
reg clk=0;always #5 clk=~clk;
reg rst=0,query=0,auth=0,command=0,stop=0,local_req=1,quiet=1,rx=1;
reg[1:0] axis=0;reg[15:0] pulse=1550;
wire tx,pc,owner,fault,stopped;wire[3:0] state;wire[31:0] accepted;wire[15:0] pan,tilt;wire[1:0] mask;
zynq_motion_s1 dut(clk,rst,query,auth,command,stop,axis,pulse,128'h12345678,local_req,quiet,1'b1,rx,pc,tx,owner,fault,stopped,state,accepted,pan,tilt,mask);
integer gen=0,tag=0,bitno,j,bi=0,ri=-1,rbit=-1,rlength=0,caseid=0,fh,kind,where,phase;
reg responding=0,pending_reply=0,cr_mode=0,sending_cr=0;integer pending_length;reg[2047:0] pending_text;reg[7:0] decoded;reg[511:0] line=0;reg[2047:0] reply;
task send_reply;input[2047:0] text;input integer length;
begin if(pending_reply)$fatal(1,"response queue overflow");pending_text=text;pending_length=length;pending_reply=1;responding=1;end endtask
task serialize_reply;input[2047:0] text;input integer length;integer z,k;reg[7:0] b;
begin responding=1;reply=text;rlength=length;
for(z=length-1;z>=0;z=z-1) begin
if(z==0&&cr_mode)begin sending_cr=1;b=13;rbit=0;rx=0;#8680;for(k=0;k<8;k=k+1)begin rbit=k+1;rx=b[k];#8680;end rbit=9;rx=1;#8680;sending_cr=0;end
ri=length-1-z;b=text[z*8+:8];rbit=0;rx=0;#8680;
for(k=0;k<8;k=k+1)begin rbit=k+1;rx=b[k];#8680;end rbit=9;rx=1;#8680;end
ri=-1;rbit=-1;responding=0;
end endtask
initial forever begin wait(pending_reply);pending_reply=0;serialize_reply(pending_text,pending_length);end
initial forever begin
@(negedge tx);tag=gen;
if(rst)begin
#4340;if(tx!==0&&tag==gen)$fatal(1,"TX start");decoded=0;
for(bitno=0;bitno<8;bitno=bitno+1)begin #8680;decoded[bitno]=tx;end
#8680;
if(tag==gen&&rst)begin
 if(tx!==1)$fatal(1,"TX stop");
 if(decoded==10) begin
 if(line=="s1q 00000000000000000000000012345678 st*ba0d") send_reply("S1SYNC 00000000000000000000000012345678 S1ACK1 1234000112340002 stopped boot 1500 1500 0 0 0*2dd6\n",98); else
if(line=="s1q 00000000000000000000000012345679 st*ccb9") send_reply("S1SYNC 00000000000000000000000012345679 S1ACK1 1234000112340002 stopped boot 1500 1500 0 0 0*b1b1\n",98); else
if(line=="s1 1234000112340002 0 arm*ec90") send_reply("S1ACK S 1234000112340002 0 ec90 arm ACCEPT REG 1234000112340002 armed ready none 1500 1500 0 1500 1500*17ed\n",108); else
if(line=="s1 1234000112340002 1 pan 1550*f20c") send_reply("S1ACK S 1234000112340002 1 f20c pan ACCEPT REG 1234000112340002 manual ready none 1550 1500 3 1550 1500*024d\n",109); else
if(line=="s1 1234000112340002 1 tlt 1550*8bed") send_reply("S1ACK S 1234000112340002 1 8bed tlt ACCEPT REG 1234000112340002 manual ready none 1500 1550 3 1500 1550*2fb6\n",109); else
if(line=="s1 1234000112340002 1 home*2744") send_reply("S1ACK S 1234000112340002 1 2744 home ACCEPT REG 1234000112340002 manual ready none 1500 1500 3 1500 1500*f76c\n",110); else
if(line=="s1 1234000112340002 1 hb*2ae3") send_reply("S1ACK S 1234000112340002 1 2ae3 hb ACCEPT REG 1234000112340002 armed ready none 1500 1500 0 1500 1500*dc28\n",107); else
if(line=="s1q 00000000000000000000000012345679 stop*0048") send_reply("S1ACK Q 00000000000000000000000012345679 - - stop ACCEPT REG 1234000112340003 stopped stop none 1500 1500 0 1500 1500*faa9\n",123); else
if(line=="s1q 0000000000000000000000001234567a stop*7d9e") send_reply("S1ACK Q 0000000000000000000000001234567a - - stop ACCEPT REG 1234000112340003 stopped stop none 1500 1500 0 1500 1500*74c1\n",123); else begin $display("unexpected complete line %s",line);$fatal(1,"unexpected command");end
 line=0;
 end else line=(line<<8)|decoded;
end else line=0;
end
end
task base;input integer armed;
begin
rst=0;gen=gen+1;query=0;auth=0;command=0;stop=0;local_req=1;quiet=1;
wait(!responding);cr_mode=0;axis=0;rx=1;line=0;#100000;rst=1;wait(owner);#100;
if(armed>=0)begin query=1;#100;query=0;wait(state==3);end
if(armed==1)begin auth=1;#100;auth=0;wait(state==4);end
end endtask
task cut;input integer category,input_pos;
begin
$fwrite(fh,"%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d\n",caseid,category,input_pos,state,dut.op,dut.tx.bit_index,ri,rbit);
$fflush(fh);rst=0;gen=gen+1;query=0;auth=0;command=0;stop=0;#100;
if(tx!==1||dut.authorized!==0||accepted!==0||state!==0)$fatal(1,"reset did not clear permission");
rst=1;wait(!responding);#200000;
if(tx!==1||dut.authorized!==0||accepted!==0||state!==0||mask!==0)$fatal(1,"old data restored state");
caseid=caseid+1;
end endtask
initial begin
fh=$fopen("reset.csv","w");$fwrite(fh,"case,category,position,state,op,tx_bit,rx_byte,rx_bit\n");
// Semantic phase coverage: IDLE, QUERY, WAIT_SYNC, AUTH, ARM, READY,
// SEND, WAIT_ACK, HEARTBEAT, STOPPING, FAULT.
for(phase=0;phase<11;phase=phase+1)begin
base(phase==0?-1:((phase<=4)?0:1));
case(phase)
0:begin end
1:begin rst=0;gen=gen+1;#100;rst=1;wait(owner);query=1;#100;query=0;wait(state==1);end
2:begin rst=0;gen=gen+1;#100;rst=1;wait(owner);query=1;#100;query=0;wait(state==2);end
3:begin end
4:begin auth=1;#100;auth=0;wait(state==1&&dut.op==1);end
5:begin end
6,7:begin command=1;#100;command=0;if(phase==6)wait(state==1);else wait(state==5);end
8:wait(state==1&&dut.op==5);
9:begin stop=1;#100;stop=0;wait(state==1&&dut.op==6);end
10:begin pulse=1701;command=1;#100;command=0;wait(state==6);pulse=1550;end
endcase
cut(0,phase);
end
// TX every bit of query, ARM, PAN, heartbeat, STOP, plus byte gap and LF.
for(kind=0;kind<7;kind=kind+1)for(where=0;where<12;where=where+1)begin
base(kind==0?-1:(kind==1?0:1));
case(kind)
0:begin query=1;#100;query=0;end
1:begin auth=1;#100;auth=0;end
2:begin command=1;#100;command=0;end
3:begin end
4:begin stop=1;#100;stop=0;end
5:begin axis=1;command=1;#100;command=0;end
6:begin axis=2;command=1;#100;command=0;end
endcase
wait(state==1&&dut.op==(kind==0?0:kind==1?1:kind==2?2:kind==3?5:kind==4?6:kind==5?3:4));
if(where<10)wait(dut.txbusy&&dut.tx.bit_index==where&&dut.tx.clocks==434);
else if(where==10)wait(dut.txdone);
else wait(dut.txbusy&&dut.outpos==dut.outlen-1&&dut.tx.bit_index==4);
cut(1+kind,where);
end
// RX bit scan and CRC/terminator/match edges on ARM ACK.
for(where=0;where<18;where=where+1)begin
base(0);cr_mode=(where==17);auth=1;#100;auth=0;wait(state==5&&dut.op==1);wait(responding);
if(where<10)wait(ri==0&&rbit==where);
else if(where==10)wait(ri==rlength-5&&rbit==4);
else if(where==11)wait(ri==rlength-1&&rbit==4);
else if(where==12)wait(dut.line_done);
else if(where==13)wait(state==4);
else if(where<17)wait(ri==rlength-(18-where)&&rbit==4);
else wait(sending_cr&&rbit==4);
cut(10,where);
end
base(1);local_req=0;wait(state==1&&dut.op==6);cut(11,0);
// Exhaust all ten serial bit phases of all four ACK CRC characters.
for(kind=0;kind<4;kind=kind+1)for(where=0;where<10;where=where+1)begin
base(0);auth=1;#100;auth=0;wait(state==5&&dut.op==1);wait(responding);
wait(ri==rlength-5+kind&&rbit==where);#4340;cut(12,kind*10+where);
end
$fclose(fh);$display("B3_RESET_PASS %0d injections; scripted replies, not MCU C",caseid);$finish;
end
initial begin #(10000000000.0);$fatal(1,"reset scan watchdog");end
endmodule
