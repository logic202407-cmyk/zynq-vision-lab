`timescale 1ns/1ps
// Clocked control producer models VIO, with the SAME reset fan-in as board insert.
module reset_cdc_audit_top(input wire clk_50m,cam_pclk,rst_n,
 input wire[7:0] controls,input wire[127:0] qid,input wire[63:0] session,
 input wire[218:0] sample,input wire sample_valid,mcu_rx,
 output wire tx,pc_tx,owner,fault,stopped,active,output wire[3:0] state,
 output wire[31:0] dropped,mdropped);
 reg[7:0] c1_controls;
 always @(posedge clk_50m)c1_controls<=controls;
 (* ASYNC_REG="TRUE" *) reg[1:0] c1_sys_release,c1_cam_release;
 wire c1_reset_async_n=rst_n&&!c1_controls[0];
 always @(posedge clk_50m or negedge c1_reset_async_n)
  if(!c1_reset_async_n)c1_sys_release<=0;else c1_sys_release<={c1_sys_release[0],1'b1};
 always @(posedge cam_pclk or negedge c1_sys_release[1])
  if(!c1_sys_release[1])c1_cam_release<=0;else c1_cam_release<={c1_cam_release[0],1'b1};
 reg[218:0] camera_sample;reg sample_strobe;
 always @(posedge cam_pclk or negedge c1_cam_release[1])
  if(!c1_cam_release[1])begin camera_sample<=0;sample_strobe<=0;end
  else begin camera_sample<=sample;sample_strobe<=sample_valid;end
 c1_observation_link #(.CLOCK_HZ(50000000),.LOCAL_RESETS(1)) c1_observation(
 clk_50m,c1_sys_release[1],cam_pclk,c1_cam_release[1],
 c1_controls[1],c1_controls[2],c1_controls[3],c1_controls[4],qid,session,
 mcu_rx,sample_strobe,camera_sample,tx,pc_tx,owner,fault,stopped,active,state,dropped,mdropped);
endmodule
