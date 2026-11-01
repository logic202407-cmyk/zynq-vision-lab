`timescale 1ns/1ps
module visual_loop_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset_n=0,start=0,scene=1;reg[15:0] pan=1500,tilt=1500;
 wire command,stop,active,fault,centered;wire[1:0] axis;wire[15:0] pulse;wire[31:0] received;
 reg valid=0;reg[7:0] byte_data=0;wire ready,tx,busy,done;
 integer commands=0,stops=0,checks=0;reg[391:0] body;reg negative=0;
 uart_tx_8n1 #(.CLOCK_HZ(100000000)) sender(clk,reset_n,1'b0,valid,byte_data,ready,tx,busy,done);
 gimbal1_visual_loop #(.PAN_SIGN(1),.TILT_SIGN(1)) dut(clk,reset_n,start,scene,1'b1,64'd1,
 tx,4'd4,1'b0,pan,tilt,command,axis,pulse,stop,active,fault,centered,received);
 wire default_active;
 gimbal1_visual_loop defaults(.clk(clk),.reset_n(reset_n),.start(start),.single_scene_confirmed(scene),
 .session_active(1'b1),.session_id(64'd1),.mcu_rx(tx),.motion_state(4'd4),.motion_fault(1'b0),
 .pan_target(pan),.tilt_target(tilt),.active(default_active));
 always @(posedge clk)begin
  if(command)begin commands=commands+1;if(axis==0)pan<=pulse;else tilt<=pulse;end
  if(stop)stops=stops+1;
  if(default_active)$fatal(1,"unconfigured direction permitted activation");
 end
 function[15:0] crcbyte;input[15:0] c;input[7:0] b;reg[15:0] v;integer k;
 begin v=c^{b,8'h00};for(k=0;k<8;k=k+1)v=v[15]?(v<<1)^16'h1021:v<<1;crcbyte=v;end endfunction
 function[7:0] hx;input[3:0] n;begin hx=n<10?48+n:87+n;end endfunction
 task sendbyte;input[7:0] b;
 begin @(negedge clk);while(!ready)@(negedge clk);byte_data=b;valid=1;@(negedge clk);valid=0;wait(done);end endtask
 task feedback;input[31:0] seq;input[63:0] session;input bad;input present;
 integer i;reg[15:0] crc;
 begin
 body="F1 0000000000000001 00000001 00000001 001e 0014 1";
 if(negative)body="F1 0000000000000001 00000001 00000001 ffe2 ffec 1";
 for(i=0;i<16;i=i+1)body[(48-(3+i))*8+:8]=hx(session[(15-i)*4+:4]);
 for(i=0;i<8;i=i+1)body[(48-(20+i))*8+:8]=hx(seq[(7-i)*4+:4]);
 body[7:0]=present?"1":"0";
 crc=16'hffff;for(i=48;i>=0;i=i-1)crc=crcbyte(crc,body[i*8+:8]);
 if(bad)crc=crc^1;
 for(i=48;i>=0;i=i-1)sendbyte(body[i*8+:8]);
 sendbyte("*");for(i=3;i>=0;i=i-1)sendbyte(hx(crc[i*4+:4]));sendbyte(10);#1000;
 end endtask
 task reset;
 begin reset_n=0;start=0;#100;reset_n=1;#100;commands=0;stops=0;pan=1500;tilt=1500;end endtask
 task enable;
 begin @(negedge clk);start=1;@(negedge clk);start=0;#100;end endtask
 initial begin
 reset;feedback(1,1,0,1);if(commands||active||received!=1)$fatal(1,"boot/feedback acceptance");checks=checks+1;
 enable;feedback(2,1,0,1);if(commands!=1||pan!=1505||tilt!=1500)$fatal(1,"single PAN step");checks=checks+1;
 feedback(3,2,0,1);if(commands!=1)$fatal(1,"wrong session accepted");checks=checks+1;
 feedback(2,1,0,1);if(commands!=1)$fatal(1,"duplicate renewed command");checks=checks+1;
 feedback(3,1,1,1);if(!fault||active||!stops)$fatal(1,"CRC did not lock fault");checks=checks+1;
 enable;feedback(4,1,0,1);if(commands!=1||active)$fatal(1,"fault auto recovered");checks=checks+1;
 reset;enable;feedback(1,1,0,0);if(!fault||active)$fatal(1,"lost target did not stop");checks=checks+1;
 reset;enable;feedback(1,1,0,1);feedback(1,1,0,1);#150000000;enable;#60000000;
 if(!fault||active||commands!=1)$fatal(1,"stale feedback lease");checks=checks+1;
 reset;feedback(1,1,0,1);if(active||commands)$fatal(1,"reset restored authorization");checks=checks+1;
 reset;negative=1;enable;feedback(1,1,0,1);
 if(commands!=1||pan!=1495||tilt!=1500)$fatal(1,"negative PAN sign");checks=checks+1;
 feedback(2,1,0,1);
 if(commands!=2||pan!=1495||tilt!=1495)$fatal(1,"negative TILT sign and axis alternation");checks=checks+1;
 $display("VISUAL_LOOP_PASS checks=%0d default_direction_disabled",checks);$finish;
 end
 initial begin #500000000;$fatal(1,"watchdog");end
endmodule
