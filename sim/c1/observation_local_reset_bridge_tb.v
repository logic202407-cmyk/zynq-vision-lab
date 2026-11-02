`timescale 1ns/1ps
// Same coupled ports and monitors as observation_bridge_tb, with the board's
// common assertion / single release per domain contract enabled explicitly.
module motion_c_bridge_tb(input wire mcu_rx,input wire[153:0] controls,
 input wire[130:0] vision_controls,input wire[31:0] camera_frame,
 output wire[104:0] bridge_sample,output wire[65:0] vision_status);
 reg clk=0,camera_clk=0;always #10 clk=~clk;always #7 camera_clk=~camera_clk;
 reg old_camera=0;
 always @(posedge camera_clk)old_camera<=vision_controls[1];
 wire tx,pc_tx,owner,fault,stopped,active;wire[3:0] state;
 wire[31:0] cdrop,mdrop;
 wire[31:0] status={16'd0,7'b0,2'd0,stopped,fault,owner,state};
 reg[31:0] count=0,errors=0;reg[7:0] last=0;
 wire[7:0] rd;wire rv,re,rb;
 assign bridge_sample={count,last,errors,status,tx};
 assign vision_status={cdrop,mdrop,fault,active};
 wire[218:0] snapshot={8'd1,16'd640,16'd480,camera_frame,camera_frame,1'b1,1'b1,
 19'd2,28'd60,28'd80,10'd10,9'd20,10'd50,9'd60};
 wire common_request_n=controls[0]&&vision_controls[2];
 (* ASYNC_REG="TRUE" *) reg[1:0] sys_release,cam_release;
 always @(posedge clk or negedge common_request_n)
  if(!common_request_n)sys_release<=0;else sys_release<={sys_release[0],1'b1};
 always @(posedge camera_clk or negedge sys_release[1])
  if(!sys_release[1])cam_release<=0;else cam_release<={cam_release[0],1'b1};
 c1_observation_link #(.CLOCK_HZ(50000000),.LOCAL_RESETS(1)) dut(
 clk,sys_release[1],camera_clk,cam_release[1],controls[151],controls[1],vision_controls[0],controls[4],
 controls[150:23],vision_controls[130:67],mcu_rx,vision_controls[1]&&!old_camera,snapshot,
 tx,pc_tx,owner,fault,stopped,active,state,cdrop,mdrop);
 uart_rx #(.CLOCK_HZ(50000000)) monitor(clk,controls[0],mcu_rx,rd,rv,re,rb);
 always @(posedge clk)if(controls[0])begin
  if(rv)begin count<=count+1;last<=rd;end
  if(re)errors<=errors+1;
 end
endmodule
