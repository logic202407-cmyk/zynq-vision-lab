// Two-axis manual calibration candidate insertion, not vendor code. Inputs are VIO-controlled.
(* ASYNC_REG="TRUE" *) reg[1:0] c1_sys_release,c1_cam_release;
wire[11:0] c1_controls;
wire[127:0] c1_query_id;
wire[63:0] c1_logging_session;
wire c1_reset_async_n=rst_n&&!c1_controls[0];
always @(posedge clk_50m or negedge c1_reset_async_n)
 if(!c1_reset_async_n)c1_sys_release<=0;else c1_sys_release<={c1_sys_release[0],1'b1};
always @(posedge cam_pclk or negedge c1_sys_release[1])
 if(!c1_sys_release[1])c1_cam_release<=0;else c1_cam_release<={c1_cam_release[0],1'b1};
wire c1_sys_reset_n=c1_sys_release[1],c1_cam_reset_n=c1_cam_release[1];
wire c1_strobe;wire[218:0] c1_snapshot;wire[31:0] c1_frame_seq,c1_capture_tick;
wire c1_owner,c1_fault,c1_stopped,c1_session_active,c1_loop_active,c1_loop_fault,c1_centered;wire[3:0] c1_state;
wire[31:0] c1_camera_dropped,c1_measurement_dropped,c1_accepted,c1_feedback_count;
wire[1:0] c1_pwm;wire[15:0] c1_pan,c1_tilt;
wire[31:0] c1_status={c1_accepted[15:0],6'd0,c1_pwm,c1_session_active,c1_stopped,c1_fault,c1_owner,c1_state};
camera_measurement_snapshot c1_pack(
 cam_pclk,c1_cam_reset_n,pl_result_strobe,pl_frame_complete,pl_target_valid,
 pl_red_count,pl_red_sum_x,pl_red_sum_y,pl_red_min_x,pl_red_max_x,
 pl_red_min_y,pl_red_max_y,c1_strobe,c1_snapshot,c1_frame_seq,c1_capture_tick);
zynq_gimbal1_loop_runtime #(.CLOCK_HZ(50000000),.LOCAL_RESETS(1)) c1_observation(
 .clk(clk_50m),.reset_n(c1_sys_reset_n),.camera_clk(cam_pclk),.camera_reset_n(c1_cam_reset_n),
 .query(c1_controls[2]),.configure(c1_controls[3]),.stop_request(c1_controls[4]),
 .authorize(c1_controls[5]),.loop_start(c1_controls[6]),.single_scene_confirmed(c1_controls[7]),
 .pan_direction(c1_controls[9:8]),.tilt_direction(c1_controls[11:10]),
 .epoch(c1_query_id),.request_local(c1_controls[1]),.pc_quiet_ack(c1_controls[1]),.pc_rx(1'b1),
 .config_nonce(64'd0),.config_session(c1_logging_session),.mcu_rx(c1_mcu_rx),
 .camera_strobe(c1_strobe),.camera_snapshot(c1_snapshot),.mcu_tx(c1_mcu_tx),.pc_tx(c1_pc_tx),
 .owner(c1_owner),.fault(c1_fault),.stop_confirmed(c1_stopped),.session_active(c1_session_active),
 .state(c1_state),.camera_dropped(c1_camera_dropped),.measurement_dropped(c1_measurement_dropped),
 .pwm_mask(c1_pwm),.accepted_count(c1_accepted),.pan_target(c1_pan),.tilt_target(c1_tilt),
 .loop_active(c1_loop_active),.loop_fault(c1_loop_fault),.centered(c1_centered),.feedback_count(c1_feedback_count));
// 0 reset, 1 ownership, 2 query, 3 bind, 4 stop, 5 arm, 6 loop start, 7 confirmed scene.
// 9:8 PAN direction, 11:10 TILT direction: 0=disabled, 1=positive, 2=negative.
// No AUTO; PWM enable remains common to both axes on the MCU.
c1_observation_vio c1_vio(.clk(clk_50m),
 .probe_in0(c1_status),.probe_in1({c1_feedback_count[28:0],c1_centered,c1_loop_fault,c1_loop_active}),
 .probe_out0(c1_controls),.probe_out1(c1_query_id),.probe_out2(c1_logging_session));
