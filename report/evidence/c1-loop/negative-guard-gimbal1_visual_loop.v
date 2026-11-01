`timescale 1ns/1ps
// Offline camera-centering candidate. No laser interface, no boot authorization.
// F1 is observation data, never an ACK. Existing B2 owns the actuator protocol.
module gimbal1_visual_loop #(
 parameter CLOCK_HZ=100000000, BAUD=115200,
 parameter PAN_SIGN=0,TILT_SIGN=0,STEP_US=5,DEADBAND=3,
 parameter MIN_US=1450,MAX_US=1550,TIMEOUT_MS=200
)(input wire clk,reset_n,start,single_scene_confirmed,session_active,
 input wire[63:0] session_id,input wire mcu_rx,
 input wire[3:0] motion_state,input wire motion_fault,
 input wire[15:0] pan_target,tilt_target,
 output reg command,output reg[1:0] axis,output reg[15:0] pulse_us,
 output reg stop_request,active,fault,centered,
 output reg[31:0] feedback_count);
 localparam OK=(PAN_SIGN==1||PAN_SIGN==-1)&&(TILT_SIGN==1||TILT_SIGN==-1)&&
 STEP_US>0&&STEP_US<=5&&MIN_US>=1300&&MAX_US<=1700&&MIN_US<MAX_US&&
 TIMEOUT_MS>0&&TIMEOUT_MS<=200&&CLOCK_HZ>=BAUD*8;
 wire[7:0] rd;wire rv,re,rb;
 uart_rx #(.CLOCK_HZ(CLOCK_HZ),.BAUD(BAUD)) receiver(clk,reset_n,mcu_rx,rd,rv,re,rb);
 reg[7:0] line[0:63];reg[6:0] length;reg overflow;
 reg[15:0] crc;reg[63:0] sid,seen_session;
 reg[31:0] seq,last_seq,plseq,msdiv,now_ms,received_at,started_at;
 reg signed[15:0] dx,dy,latest_dx,latest_dy;
 reg valid_line,dirty,seen,old_start,prefer_tilt;
 integer i,n,next_value;reg[15:0] received_crc;
 function[15:0] crcbyte;
 input[15:0] c;input[7:0] b;integer k;reg[15:0] v;
 begin v=c^{b,8'h00};for(k=0;k<8;k=k+1)v=v[15]?(v<<1)^16'h1021:v<<1;crcbyte=v;end
 endfunction
 function integer hex;
 input[7:0] c;
 begin if(c>=48&&c<=57)hex=c-48;else if(c>=97&&c<=102)hex=c-87;else hex=-1;end
 endfunction
 task fail_closed;
 begin active<=0;fault<=1;centered<=0;dirty<=0;stop_request<=1;command<=0;end
 endtask
 always @(posedge clk or negedge reset_n)begin
 if(!reset_n)begin
  length<=0;overflow<=0;command<=0;axis<=0;pulse_us<=1500;
  stop_request<=0;active<=0;fault<=0;centered<=0;feedback_count<=0;
  last_seq<=0;seen<=0;seen_session<=0;dirty<=0;old_start<=0;
  prefer_tilt<=0;latest_dx<=0;latest_dy<=0;
  msdiv<=0;now_ms<=0;received_at<=0;started_at<=0;
 end else begin
  command<=0;stop_request<=0;old_start<=start;
  if(msdiv==CLOCK_HZ/1000-1)begin msdiv<=0;now_ms<=now_ms+1;end else msdiv<=msdiv+1;
  if(!session_active||session_id!=seen_session)begin
   seen<=0;dirty<=0;last_seq<=0;seen_session<=session_id;
   if(active)fail_closed;
  end
  if(start&&!old_start&&!fault&&OK&&single_scene_confirmed&&session_active&&motion_state==4)begin
   active<=1;dirty<=0;centered<=0;started_at<=now_ms;received_at<=now_ms;
  end
  if(active)begin
   if(!single_scene_confirmed||!session_active||motion_fault||motion_state==0||motion_state==3||motion_state==6||
      now_ms-received_at>=TIMEOUT_MS)fail_closed;
   else if(dirty&&motion_state==4)begin
    dirty<=0;centered<=0;
    if((latest_dx>DEADBAND||latest_dx< -DEADBAND)&&
       (!prefer_tilt||(latest_dy<=DEADBAND&&latest_dy>=-DEADBAND)))begin
     axis<=0;prefer_tilt<=1;
     next_value=pan_target+((latest_dx>0)?PAN_SIGN*STEP_US:-PAN_SIGN*STEP_US);
     if(next_value<MIN_US||next_value>MAX_US)fail_closed;
     else begin pulse_us<=next_value;command<=1;end
    end else if(latest_dy>DEADBAND||latest_dy< -DEADBAND)begin
     axis<=1;prefer_tilt<=0;
     next_value=tilt_target+((latest_dy>0)?TILT_SIGN*STEP_US:-TILT_SIGN*STEP_US);
     if(next_value<MIN_US||next_value>MAX_US)fail_closed;
     else begin pulse_us<=next_value;command<=1;end
    end else centered<=1;
   end
  end
  if(re)begin length<=0;overflow<=0;if(active)fail_closed;end
  else if(rv)begin
   if(rd==10)begin
    if(length>=2&&line[0]=="F"&&line[1]=="1")begin
     valid_line=!overflow&&length==54;
     crc=16'hffff;for(i=0;i<49;i=i+1)crc=crcbyte(crc,line[i]);
     sid=0;seq=0;plseq=0;dx=0;dy=0;received_crc=0;
     for(i=0;i<54;i=i+1)begin
      if((i>=3&&i<=18)||(i>=20&&i<=27)||(i>=29&&i<=36)||
         (i>=38&&i<=41)||(i>=43&&i<=46)||(i>=50&&i<=53))begin
       n=hex(line[i]);if(n<0)valid_line=0;
       if(i<=18)sid=(sid<<4)|n;
       else if(i<=27)seq=(seq<<4)|n;
       else if(i<=36)plseq=(plseq<<4)|n;
       else if(i<=41)dx=(dx<<4)|n;
       else if(i<=46)dy=(dy<<4)|n;
       else received_crc=(received_crc<<4)|n;
      end
     end
     if(line[2]!=32||line[19]!=32||line[28]!=32||line[37]!=32||line[42]!=32||line[47]!=32||line[49]!=42||
        (line[48]!="0"&&line[48]!="1")||crc!=received_crc)valid_line=0;
     if(!valid_line)begin if(active)fail_closed;end
     else if(session_active&&sid==session_id&&(!seen||seq>last_seq))begin
      seen<=1;last_seq<=seq;feedback_count<=feedback_count+1;
      if(active)begin
       if(line[48]!="1"||dx< -80||dx>79||dy< -59||dy>60)fail_closed;
       else begin latest_dx<=dx;latest_dy<=dy;received_at<=now_ms;dirty<=1;end
      end
     end
    end
    length<=0;overflow<=0;
   end else if(length<64)begin line[length]<=rd;length<=length+1;end else overflow<=1;
  end
 end
 end
endmodule
