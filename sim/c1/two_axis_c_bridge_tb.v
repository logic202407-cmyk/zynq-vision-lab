`timescale 1ns/1ps
module motion_c_bridge_tb(input wire mcu_rx,input wire[153:0] controls,
 input wire[130:0] vision_controls,input wire[31:0] camera_frame,
 output wire[104:0] bridge_sample,output wire[65:0] vision_status);
 reg clk=0,camera_clk=0;always #5 clk=~clk;always #7 camera_clk=~camera_clk;
 reg old_camera=0;always @(posedge camera_clk)old_camera<=vision_controls[1];
 wire tx,pc_tx,owner,fault,stopped,active,rejected;wire[3:0] state;
 wire[31:0] accepted,cdrop,mdrop;wire[15:0] pan,tilt;wire[1:0] mask;
 wire[31:0] status={accepted[15:0],7'b0,mask,stopped,fault,owner,state};
 reg[31:0] count=0,errors=0;reg[7:0] last=0;wire[7:0] rd;wire rv,re,rb;
 assign bridge_sample={count,last,errors,status,tx};
 assign vision_status={cdrop,mdrop,fault,active};
 wire[218:0] snapshot={8'd1,16'd640,16'd480,camera_frame,camera_frame,1'b1,1'b1,
  19'd2,28'd60,28'd80,10'd10,9'd20,10'd50,9'd60};
 c1_two_axis_step_link #(.CLOCK_HZ(100000000),.LOCAL_RESETS(0)) dut(
  .clk(clk),.reset_n(controls[0]),.camera_clk(camera_clk),.camera_reset_n(vision_controls[2]),
  .acquire(controls[151]),.query(controls[1]),.configure(vision_controls[0]),
  .stop_request(controls[4]),.authorize(controls[2]),
  .step(controls[3]&&controls[22:7]==1550),.center(controls[3]&&controls[22:7]==1500),
  .axis_select(controls[6:5]),
  .query_id(controls[150:23]),.logging_session(vision_controls[130:67]),.mcu_rx(mcu_rx),
  .camera_strobe(vision_controls[1]&&!old_camera),.camera_snapshot(snapshot),
  .mcu_tx(tx),.pc_tx(pc_tx),.owner(owner),.fault(fault),.stop_confirmed(stopped),
  .session_active(active),.rejected(rejected),.state(state),.camera_dropped(cdrop),
  .measurement_dropped(mdrop),.pwm_mask(mask),.accepted_count(accepted),.pan_target(pan),.tilt_target(tilt));
 uart_rx #(.CLOCK_HZ(100000000)) monitor(clk,controls[0],mcu_rx,rd,rv,re,rb);
 always @(posedge clk)if(controls[0])begin
  if(rv)begin count<=count+1;last<=rd;end
  if(re)errors<=errors+1;
 end
endmodule
