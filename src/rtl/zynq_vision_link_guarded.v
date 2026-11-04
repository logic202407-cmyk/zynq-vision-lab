`timescale 1ns/1ps
// Offline integration top. Operator/configuration inputs are synchronous clk strobes.
// Existing B2 UART is captured as COMPLETE lines then serialized by one physical TX.
module zynq_vision_link_guarded #(parameter CLOCK_HZ=100000000,BAUD=115200,LOCAL_RESETS=0,ALLOW_AUTO=0)(
 input wire clk,reset_n,camera_clk,camera_reset_n,
 input wire query,authorize,command,stop_request,input wire[1:0] axis,input wire[15:0] pulse_us,
 input wire[127:0] epoch,input wire request_local,pc_quiet_ack,pc_rx,mcu_rx,
 input wire configure,input wire[63:0] config_nonce,config_session,
 input wire camera_strobe,input wire[218:0] camera_snapshot,
 output wire pc_tx,mcu_tx,owner,fault,stop_confirmed,session_active,
 output wire[3:0] state,output wire[31:0] accepted_count,
 output wire[15:0] pan_target,tilt_target,output wire[1:0] pwm_mask,
 output wire[31:0] camera_dropped,measurement_dropped,output wire command_ready
);
 wire motion_tx,motion_fault,queue_fault,scheduler_fault,session_fault;
 wire cv,cr,bv,br,vv,vr,pending,idle;wire[7:0] cd,bd,vd;
 wire[63:0] bound_session;
 wire nonce_valid;wire[63:0] discovered_nonce;
 wire mbusy,mdone;
 wire local_fault=queue_fault||scheduler_fault;
 assign fault=motion_fault||local_fault;
 zynq_motion_s1_guarded #(.CLOCK_HZ(CLOCK_HZ),.BAUD(BAUD),.ALLOW_AUTO(ALLOW_AUTO)) motion(
 clk,reset_n,query,authorize,command,stop_request||local_fault||(!request_local&&owner),axis,pulse_us,epoch,
 request_local||!idle||pending||mbusy||bv,pc_quiet_ack,pc_rx,mcu_rx,pc_tx,motion_tx,owner,motion_fault,stop_confirmed,state,accepted_count,pan_target,tilt_target,pwm_mask,command_ready);
 uart_line_queue #(.CLOCK_HZ(CLOCK_HZ),.BAUD(BAUD)) commands(clk,reset_n,owner?motion_tx:1'b1,cv,cd,cr,queue_fault,pending);
 wire urgent=state==1||pending||stop_request||local_fault||!request_local||!pc_quiet_ack;
 measurement_nonce_observer #(.CLOCK_HZ(CLOCK_HZ),.BAUD(BAUD)) discovery(
 clk,reset_n,query&&owner&&(state==0||state==6),!owner||state==0||state==6,epoch,mcu_rx,nonce_valid,discovered_nonce);
 reg encoder_reset_n,config_reset_n;
 // In board mode both local resets assert from the SAME request. The system
 // reset alone flushes configuration; the camera release is not a new request.
 wire config_arst_n=LOCAL_RESETS?reset_n:(reset_n&&camera_reset_n);
 (* ASYNC_REG="TRUE", SHREG_EXTRACT="NO" *) reg[1:0] config_release;
 always @(posedge clk or negedge config_arst_n)begin
  if(!config_arst_n)config_release<=0;else config_release<={config_release[0],1'b1};
 end
 // Operational flush is registered; do not feed combinational state decodes to reset trees.
 always @(posedge clk or negedge reset_n)begin
  if(!reset_n)encoder_reset_n<=0;else encoder_reset_n<=!(idle&&urgent);
 end
 always @(posedge clk or negedge config_release[1])begin
  if(!config_release[1])config_reset_n<=0;
  else config_reset_n<=(request_local||!idle)&&state!=0&&state!=6;
 end
 measurement_session #(.CLOCK_HZ(CLOCK_HZ),.BAUD(BAUD)) config_link(
 clk,config_reset_n,configure,owner&&state==3&&!urgent&&nonce_valid&&(config_nonce==0||config_nonce==discovered_nonce),discovered_nonce,config_session,
 mcu_rx,br,bv,bd,session_active,session_fault,bound_session);
 wire[218:0] snapshot;wire sv,sr,source_ready;
 vision_snapshot_cdc #(.WIDTH(219),.LOCAL_RESETS(LOCAL_RESETS)) cdc(camera_clk,clk,camera_reset_n,reset_n,
 camera_strobe,camera_snapshot,source_ready,camera_dropped,sv,snapshot,sr);
 // Discard out-of-session snapshots instead of retaining stale frames for a later session.
 assign sr=!mbusy;
 vision_measurement_tx measurement(
 .clk(clk),.rst_n(encoder_reset_n),.capture(sv&&sr),
 .control_pending(urgent||!session_active||!owner||!(state==3||state==4)),
 .camera_id(8'd0),.mask_version(snapshot[218:211]),.session_id(bound_session),
 .width(snapshot[210:195]),.height(snapshot[194:179]),
 .frame_seq(snapshot[178:147]),.capture_tick(snapshot[146:115]),.timestamp_valid(1'b1),
 .complete(snapshot[114]),.target(snapshot[113]),.count(snapshot[112:94]),
 .sum_x(snapshot[93:66]),.sum_y(snapshot[65:38]),.xmin(snapshot[37:28]),
 .ymin(snapshot[27:19]),.xmax(snapshot[18:9]),.ymax(snapshot[8:0]),
 .data(vd),.valid(vv),.ready(vr),.busy(mbusy),.done(mdone),.dropped(measurement_dropped));
 wire physical_tx;
 uart_line_scheduler #(.CLOCK_HZ(CLOCK_HZ),.BAUD(BAUD)) scheduler(
 clk,reset_n,owner,urgent,cv,cd,cr,bv,bd,br,vv,vd,vr,physical_tx,scheduler_fault,idle);
 assign mcu_tx=!reset_n?1'b1:owner?physical_tx:pc_rx;
endmodule
