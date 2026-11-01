// Original insertion template for a private vendor camera top. No vendor code.
(* ASYNC_REG="TRUE" *) reg[1:0] c1_sys_release,c1_cam_release;
wire[7:0] c1_controls;
wire[127:0] c1_query_id;
wire[63:0] c1_logging_session;
wire c1_reset_async_n=rst_n&&!c1_controls[0];
always @(posedge clk_50m or negedge c1_reset_async_n)
 if(!c1_reset_async_n)c1_sys_release<=0;else c1_sys_release<={c1_sys_release[0],1'b1};
always @(posedge cam_pclk or negedge c1_reset_async_n)
 if(!c1_reset_async_n)c1_cam_release<=0;else c1_cam_release<={c1_cam_release[0],1'b1};
wire c1_sys_reset_n=c1_sys_release[1],c1_cam_reset_n=c1_cam_release[1];
wire c1_strobe;wire[218:0] c1_snapshot;wire[31:0] c1_frame_seq,c1_capture_tick;
wire c1_owner,c1_fault,c1_stopped,c1_session_active;wire[3:0] c1_state;
wire[31:0] c1_camera_dropped,c1_measurement_dropped;
wire[31:0] c1_status={24'd0,c1_session_active,c1_stopped,c1_fault,c1_owner,c1_state};
camera_measurement_snapshot c1_pack(
 cam_pclk,c1_cam_reset_n,pl_result_strobe,pl_frame_complete,pl_target_valid,
 pl_red_count,pl_red_sum_x,pl_red_sum_y,pl_red_min_x,pl_red_max_x,
 pl_red_min_y,pl_red_max_y,c1_strobe,c1_snapshot,c1_frame_seq,c1_capture_tick);
c1_observation_link #(.CLOCK_HZ(50000000)) c1_observation(
 clk_50m,c1_sys_reset_n,cam_pclk,c1_cam_reset_n,
 c1_controls[1],c1_controls[2],c1_controls[3],c1_controls[4],
 c1_query_id,c1_logging_session,c1_mcu_rx,c1_strobe,c1_snapshot,
 c1_mcu_tx,c1_pc_tx,c1_owner,c1_fault,c1_stopped,c1_session_active,c1_state,
 c1_camera_dropped,c1_measurement_dropped);
// Controls are synchronous clk_50m VIO outputs. All design-time values are zero.
// No ARM or position control exists. Epoch uniqueness for motion remains blocked.
c1_observation_vio c1_vio(.clk(clk_50m),
 .probe_in0(c1_status),.probe_in1(c1_measurement_dropped),
 .probe_out0(c1_controls),.probe_out1(c1_query_id),.probe_out2(c1_logging_session));
