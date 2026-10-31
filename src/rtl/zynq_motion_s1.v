`timescale 1ns/1ps
// Offline candidate: synchronous, debounced operator strobes; epoch must be fresh
// across resets. No pins or real clock are assumed. No automatic boot traffic.
module zynq_motion_s1 #(
 parameter integer CLOCK_HZ=100000000, BAUD=115200,
 parameter integer ACK_MS=100, HEARTBEAT_MS=100, AUTH_MS=30000, TX_MS=10
)(
 input wire clk,reset_n,query,authorize,command,stop_request,
 input wire [1:0] axis, // 0 pan, 1 tlt, 2 home; 3 invalid
 input wire [15:0] pulse_us,
 input wire [127:0] epoch,
 input wire request_local,pc_quiet_ack,pc_rx,mcu_rx,
 output wire pc_tx,mcu_tx,
 output reg owner, fault, stop_confirmed,
 output reg [3:0] state,
 output reg [31:0] accepted_count,
 output reg [15:0] pan_target,tilt_target,
 output reg [1:0] pwm_mask
);
 localparam IDLE=0,SEND=1,WAIT_SYNC=2,AUTH=3,READY=4,WAIT_ACK=5,FAULT=6;
 localparam OP_QUERY=0,OP_ARM=1,OP_PAN=2,OP_TLT=3,OP_HOME=4,OP_HB=5,OP_STOP=6;
 localparam DIV=(CLOCK_HZ+BAUD/2)/BAUD;
 localparam CONFIG_OK=BAUD>0&&CLOCK_HZ>=8*BAUD&&ACK_MS>0&&
 HEARTBEAT_MS>0&&HEARTBEAT_MS<500&&AUTH_MS>0&&TX_MS>0;
 reg [6:0] old_inputs;
 wire qe=query&&!old_inputs[0], ae=authorize&&!old_inputs[1];
 wire ce=command&&!old_inputs[2], se=stop_request&&!old_inputs[3];
 reg [31:0] msdiv, now_ms,deadline,auth_at,live_at,idle_clocks,seq;
 reg authorized,recheck,cancel_pending,send_wait,reviewed_fault;
 reg [2:0] op;
 reg [127:0] qid,last_epoch;
 reg [63:0] nonce;
 reg [15:0] expected_pan,expected_tlt,request_crc;
 reg [1:0] expected_mask;
 reg [7:0] outbuf[0:63];
 integer outlen,outpos,seqdigits,bodylen,pos;
 reg [31:0] seqwork;
 reg [79:0] decimal_digits;
 reg preparing,tx_loaded;
 reg [7:0] tx_latch;
 reg [7:0] buildbyte;
 reg [15:0] calc_crc;
 reg building;
 wire txready,txbusy,txdone,local_tx;
 wire [7:0] rd;
 wire rv,re,rb;
 wire txvalid=state==SEND&&!building&&!send_wait&&tx_loaded;
 wire [7:0] txdata=outbuf[outpos[5:0]];
 (* KEEP_HIERARCHY="yes" *) uart_tx_8n1 #(.CLOCK_HZ(CLOCK_HZ),.BAUD(BAUD)) tx(
 .clk(clk),.reset_n(reset_n),.stop(1'b0),.valid(txvalid),.data(tx_latch),
 .ready(txready),.tx(local_tx),.busy(txbusy),.done(txdone));
 uart_rx #(.CLOCK_HZ(CLOCK_HZ),.BAUD(BAUD)) rx(clk,reset_n,mcu_rx,rd,rv,re,rb);
 assign pc_tx=mcu_rx;
 assign mcu_tx=!reset_n?1'b1:(owner?local_tx:pc_rx);
 // Bounded token/CRC parser. Unrelated periodic status cannot satisfy an ACK.
 reg [255:0] tok[0:19];
 reg [5:0] lens[0:19];
 reg [31:0] number[0:19];
 reg numeric[0:19];
 integer ti,total,hexcount,i;
 reg star,parse_bad,line_done,line_good;
 reg [15:0] rxcrc,wirecrc;
 function [15:0] crcbyte;
 input [15:0] c;input [7:0] b;integer k;reg [15:0] v;
 begin v=c^{b,8'h00};for(k=0;k<8;k=k+1) v=v[15]?(v<<1)^16'h1021:v<<1;crcbyte=v;end
 endfunction
 function [7:0] hx;input [3:0] v;begin hx=v<10?8'd48+v:8'd87+v;end endfunction
 function [4:0] unhex;input [7:0] c;
 begin if(c>=48&&c<=57) unhex=c-48;else if(c>=97&&c<=102) unhex=c-87;else unhex=16;end endfunction
 function [63:0] hexnum;input [255:0] s;integer k;reg [63:0] v;
 begin v=0;for(k=15;k>=0;k=k-1) v=(v<<4)|unhex(s[k*8 +:8]);hexnum=v;end endfunction
 function [127:0] hexwide;input [255:0] s;integer k;reg [127:0] v;
 begin v=0;for(k=31;k>=0;k=k-1) v=(v<<4)|unhex(s[k*8 +:8]);hexwide=v;end endfunction
 function reason_valid;input [255:0] s;
 begin reason_valid=s=="boot"||s=="stop"||s=="ready"||s=="link_timeout"||s=="stale"||s=="parse"||s=="uart"||s=="key"||s=="vision"||s=="entropy";end endfunction
 function hexvalid;input [255:0] s;input integer n;integer k;reg ok;
 begin ok=1;for(k=0;k<32;k=k+1) if(k<n&&unhex(s[k*8 +:8])>15) ok=0;hexvalid=ok;end endfunction
 always @(posedge clk or negedge reset_n) begin
 if(!reset_n) begin
 ti<=0;total<=0;star<=0;parse_bad<=0;hexcount<=0;rxcrc<=16'hffff;wirecrc<=0;line_done<=0;line_good<=0;
 for(i=0;i<20;i=i+1) begin tok[i]<=0;lens[i]<=0;number[i]<=0;numeric[i]<=1;end
 end else begin
 line_done<=0;
 if(rv) begin
 if(rd==10) begin line_done<=1;line_good<=!parse_bad&&star&&hexcount==4&&wirecrc==rxcrc;
 total<=0;star<=0;parse_bad<=0;hexcount<=0;rxcrc<=16'hffff;wirecrc<=0;ti<=0;
 end else if(rd!=13) begin
 if(total==0) begin for(i=0;i<20;i=i+1) begin tok[i]<=0;lens[i]<=0;number[i]<=0;numeric[i]<=1;end end
 total<=total+1;
 if(total>=254) parse_bad<=1;
 if(star) begin if(hexcount>=4||unhex(rd)>15) parse_bad<=1;
 wirecrc<=(wirecrc<<4)|unhex(rd);hexcount<=hexcount+1;end
 else if(rd==42) star<=1;
 else begin
 rxcrc<=crcbyte(rxcrc,rd);
 if(rd==32) begin if(ti>=19||lens[ti]==0) parse_bad<=1;else ti<=ti+1;end
 else if(ti<20) begin if(lens[ti]>=32) parse_bad<=1;
 number[ti]<=total==0?0:number[ti]*10+rd-48;
 numeric[ti]<=total!=0&&numeric[ti]&&rd>=48&&rd<=57&&
 (number[ti]<429496729||(number[ti]==429496729&&rd<=53));
 tok[ti]<=total==0?rd:(tok[ti]<<8)|rd;lens[ti]<=total==0?1:lens[ti]+1;end
 end
 end
 end
 end
 end
 // One byte written per clock; one constant-divisor decimal digit per clock.
 // Avoid a wide variable-position barrel shifter for the whole request string.
 always @* begin
 buildbyte=0;bodylen=0;pos=0;
 if(op==OP_QUERY||op==OP_STOP) begin
 bodylen=op==OP_QUERY?39:41;
 if(outlen==0) buildbyte="s";else if(outlen==1) buildbyte="1";
 else if(outlen==2) buildbyte="q";else if(outlen==3||outlen==36) buildbyte=" ";
 else if(outlen<36) buildbyte=hx(qid[(35-outlen)*4 +:4]);
 else if(outlen==37) buildbyte="s";else if(outlen==38) buildbyte="t";
 else if(outlen==39) buildbyte="o";else buildbyte="p";
 end else begin
 bodylen=21+seqdigits+((op==OP_ARM)?3:(op==OP_HB)?2:(op==OP_HOME)?4:8);
 if(outlen==0) buildbyte="s";else if(outlen==1) buildbyte="1";
 else if(outlen==2||outlen==19||outlen==20+seqdigits) buildbyte=" ";
 else if(outlen<19) buildbyte=hx(nonce[(18-outlen)*4 +:4]);
 else if(outlen<20+seqdigits) buildbyte=decimal_digits[(seqdigits-1-(outlen-20))*8 +:8];
 else begin
 pos=outlen-21-seqdigits;
 case(op)
 OP_ARM:case(pos) 0:buildbyte="a";1:buildbyte="r";default:buildbyte="m";endcase
 OP_HB:buildbyte=pos==0?"h":"b";
 OP_HOME:case(pos) 0:buildbyte="h";1:buildbyte="o";2:buildbyte="m";default:buildbyte="e";endcase
 default:begin
 case(pos)
 0:buildbyte=op==OP_PAN?"p":"t";
 1:buildbyte=op==OP_PAN?"a":"l";
 2:buildbyte=op==OP_PAN?"n":"t";
 3:buildbyte=" ";
 4:buildbyte=48+(op==OP_PAN?expected_pan:expected_tlt)/1000;
 5:buildbyte=48+((op==OP_PAN?expected_pan:expected_tlt)/100)%10;
 6:buildbyte=48+((op==OP_PAN?expected_pan:expected_tlt)/10)%10;
 default:buildbyte=48+(op==OP_PAN?expected_pan:expected_tlt)%10;
 endcase end
 endcase end
 end
 end
 // Storage has a single synchronous write port and needs no reset: valid
 // bytes are constructed before transmission; reset aborts the controller.
 always @(posedge clk) if(reset_n&&state==SEND&&building&&!preparing) begin
 if(outlen<bodylen) outbuf[outlen]<=buildbyte;
 else if(outlen==bodylen) outbuf[outlen]<=42;
 else if(outlen<bodylen+5) outbuf[outlen]<=hx(calc_crc[(bodylen+4-outlen)*4 +:4]);
 else outbuf[outlen]<=10;
 end
 task launch;input [2:0] operation;
 begin
 op<=operation;outlen<=0;outpos<=0;calc_crc<=16'hffff;
 building<=1;preparing<=1;seqwork<=seq;seqdigits<=0;decimal_digits<=0;
 send_wait<=0;tx_loaded<=0;state<=SEND;deadline<=now_ms;
 end endtask
 wire sync_match=tok[0]=="S1SYNC" && hexwide(tok[1])==qid && hexvalid(tok[1],32) && lens[1]==32 && tok[2]=="S1ACK1";
 wire sync_ok=reason_valid(tok[5])&&lens[3]==16&&hexvalid(tok[3],16)&&hexnum(tok[3])!=0&&
 (tok[4]=="stopped"||tok[4]=="fault")&&tok[8]=="0"&&
 (numeric[6]&&lens[6]>0&&lens[6]<=10)&&(numeric[7]&&lens[7]>0&&lens[7]<=10)&&
 number[6]>=1300&&number[6]<=1700&&number[7]>=1300&&number[7]<=1700&&
 tok[9]=="0"&&(numeric[10]&&lens[10]>0&&lens[10]<=10)&&lens[11]==0;
 wire identity_s=tok[1]=="S"&&lens[2]==16&&hexvalid(tok[2],16)&&hexnum(tok[2])==nonce&&
 (numeric[3]&&lens[3]>0&&lens[3]<=10)&&number[3]==seq&&lens[4]==4&&hexvalid(tok[4],4)&&tok[4]=={hx(request_crc[15:12]),hx(request_crc[11:8]),hx(request_crc[7:4]),hx(request_crc[3:0])};
 wire opcode_ok=(op==OP_ARM&&tok[5]=="arm")||(op==OP_PAN&&tok[5]=="pan")||
 (op==OP_TLT&&tok[5]=="tlt")||(op==OP_HOME&&tok[5]=="home")||(op==OP_HB&&tok[5]=="hb");
 wire identity_q=op==OP_STOP&&tok[1]=="Q"&&hexwide(tok[2])==qid&&hexvalid(tok[2],32)&&lens[2]==32&&tok[3]=="-"&&tok[4]=="-"&&tok[5]=="stop";
 wire ack_match=tok[0]=="S1ACK"&&(identity_q||(identity_s&&opcode_ok));
 wire ack_fields=reason_valid(tok[10])&&tok[6]=="ACCEPT"&&tok[7]=="REG"&&lens[8]==16&&hexvalid(tok[8],16)&&
 tok[11]=="none"&&lens[17]==0&&(numeric[12]&&lens[12]>0&&lens[12]<=10)&&(numeric[13]&&lens[13]>0&&lens[13]<=10)&&
 (numeric[14]&&lens[14]>0&&lens[14]<=10)&&(numeric[15]&&lens[15]>0&&lens[15]<=10)&&(numeric[16]&&lens[16]>0&&lens[16]<=10);
 wire targets_ok=number[12]==expected_pan&&number[13]==expected_tlt&&number[14]==expected_mask&&
 (expected_mask==0||(number[15]==expected_pan&&number[16]==expected_tlt));
 always @(posedge clk or negedge reset_n) begin
 if(!reset_n) begin
 state<=IDLE;owner<=0;fault<=0;stop_confirmed<=0;old_inputs<=0;msdiv<=0;now_ms<=0;
 deadline<=0;auth_at<=0;live_at<=0;idle_clocks<=0;seq<=0;authorized<=0;recheck<=0;reviewed_fault<=0;
 cancel_pending<=0;qid<=0;last_epoch<=0;nonce<=0;op<=0;outlen<=0;outpos<=0;seqdigits<=0;seqwork<=0;decimal_digits<=0;preparing<=0;tx_loaded<=0;tx_latch<=0;
 building<=0;calc_crc<=16'hffff;request_crc<=0;send_wait<=0;
 pan_target<=1500;tilt_target<=1500;pwm_mask<=0;expected_pan<=1500;expected_tlt<=1500;expected_mask<=0;accepted_count<=0;
 end else begin
 old_inputs<={3'b0,stop_request,command,authorize,query};
 if(msdiv==CLOCK_HZ/1000-1) begin msdiv<=0;now_ms<=now_ms+1;end else msdiv<=msdiv+1;
 if(!pc_rx||!mcu_rx||rb||txbusy||!pc_quiet_ack) idle_clocks<=0;
 else if(idle_clocks<12*DIV) idle_clocks<=idle_clocks+1;
 if(CONFIG_OK&&!owner&&request_local&&pc_quiet_ack&&idle_clocks==12*DIV&&state==IDLE) owner<=1;
 if(owner&&!request_local&&stop_confirmed&&state==IDLE&&idle_clocks==12*DIV) owner<=0;
 if(se || (owner&&(!request_local||!pc_quiet_ack)&&!stop_confirmed&&op!=OP_STOP) ||
 (authorized&&now_ms-auth_at>=AUTH_MS)) begin authorized<=0;cancel_pending<=1;end
 if(re&&owner&&state!=IDLE&&state!=FAULT) begin
 authorized<=0;fault<=1;
 if(op!=OP_STOP) cancel_pending<=1;
 else if(state!=SEND) state<=FAULT;
 end
 case(state)
 IDLE,FAULT:if(qe&&owner&&epoch!=0&&epoch!=last_epoch) begin
 qid=epoch;last_epoch<=epoch;recheck<=0;authorized<=0;cancel_pending<=0;fault<=0;stop_confirmed<=0;launch(OP_QUERY);end
 SEND:begin
 if(building) begin
 if(preparing) begin
 decimal_digits[seqdigits*8 +:8]<=48+seqwork%10;seqdigits<=seqdigits+1;seqwork<=seqwork/10;
 if(seqwork<10) preparing<=0;
 end else if(outlen<bodylen) begin
 calc_crc<=crcbyte(calc_crc,buildbyte);outlen<=outlen+1;
 end else if(outlen==bodylen) begin request_crc<=calc_crc;outlen<=outlen+1;end
 else if(outlen<bodylen+5) begin outlen<=outlen+1;end
 else begin outlen<=outlen+1;building<=0;end
 end else if(!send_wait&&!tx_loaded) begin tx_latch<=txdata;tx_loaded<=1;end
 else if(!send_wait&&txready) begin send_wait<=1;tx_loaded<=0;end
 else if(send_wait&&txdone) begin
 send_wait<=0;
 if(outpos==outlen-1) begin deadline<=now_ms;state<=op==OP_QUERY?WAIT_SYNC:WAIT_ACK;end
 else outpos<=outpos+1;
 end
 end
 WAIT_SYNC:begin
 if(line_done&&sync_match) begin
 if(!line_good||!sync_ok) begin fault<=1;cancel_pending<=1;end
 else if(recheck) begin
 if((tok[4]=="fault")!=reviewed_fault || hexnum(tok[3])!=nonce || number[6]!=pan_target || number[7]!=tilt_target) begin fault<=1;authorized<=0;state<=FAULT;end
 else begin seq=0;expected_mask<=0;launch(OP_ARM);end
 end else begin reviewed_fault<=tok[4]=="fault";nonce<=hexnum(tok[3]);pan_target<=number[6];tilt_target<=number[7];
 expected_pan<=number[6];expected_tlt<=number[7];pwm_mask<=0;stop_confirmed<=1;state<=AUTH;end
 end
 if(now_ms-deadline>=ACK_MS) begin fault<=1;cancel_pending<=1;end
 end
 AUTH:if(ae&&owner&&pc_quiet_ack&&request_local) begin
 if(qid==128'hffffffffffffffffffffffffffffffff) begin fault<=1;state<=FAULT;end
 else begin qid=qid+1;last_epoch<=qid;recheck<=1;authorized<=1;auth_at<=now_ms;stop_confirmed<=0;launch(OP_QUERY);end
 end
 READY:begin
 if(ce) begin
 if(axis==3||(axis!=2&&(pulse_us<1300||pulse_us>1700))||seq==32'hffffffff) begin fault<=1;cancel_pending<=1;end
 else begin seq=seq+1;expected_mask=3;
 if(axis==0) begin expected_pan=pulse_us;launch(OP_PAN);end
 else if(axis==1) begin expected_tlt=pulse_us;launch(OP_TLT);end
 else begin expected_pan=1500;expected_tlt=1500;launch(OP_HOME);end
 end
 end else if(now_ms-live_at>=HEARTBEAT_MS) begin
 if(seq==32'hffffffff) begin fault<=1;cancel_pending<=1;end
 else begin seq=seq+1;launch(OP_HB);end
 end
 end
 WAIT_ACK:begin
 if(line_done&&ack_match) begin
 if(line_good&&ack_fields&&((op==OP_STOP&&number[14]==0&&(tok[9]=="stopped"||tok[9]=="fault"))||
 (op!=OP_STOP&&hexnum(tok[8])==nonce&&targets_ok&&((op==OP_ARM&&tok[9]=="armed")||
 (op!=OP_ARM&&(tok[9]=="armed"||tok[9]=="manual")))))) begin
 accepted_count<=accepted_count+1;pwm_mask<=number[14];pan_target<=number[12];tilt_target<=number[13];
 if(op==OP_STOP) begin stop_confirmed<=1;authorized<=0;state<=fault?FAULT:IDLE;end
 else begin live_at<=deadline;state<=READY;end
 end else begin fault<=1;authorized<=0;if(op==OP_STOP) state<=FAULT;else cancel_pending<=1;end
 end
 if(now_ms-deadline>=ACK_MS) begin fault<=1;authorized<=0;if(op==OP_STOP) state<=FAULT;else cancel_pending<=1;end
 end
 default:begin state<=FAULT;authorized<=0;fault<=1;end
 endcase
 // A stalled serializer cannot hold the FSM forever. Abort only at a byte
 // boundary; the MCU independently rejects/ages any incomplete command.
 if(state==SEND&&now_ms-deadline>=TX_MS) begin
 fault<=1;authorized<=0;cancel_pending<=0;
 if(!txbusy) state<=FAULT;
 end
 // Complete a transmitted line before stopping; never splice a frame.
 if(cancel_pending&&state!=SEND) begin
 cancel_pending<=0;authorized<=0;recheck<=0;stop_confirmed<=0;
 qid=qid+1;last_epoch<=qid;launch(OP_STOP);
 end
 end
 end
endmodule
