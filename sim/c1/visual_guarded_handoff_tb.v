`timescale 1ns/1ps
module visual_guarded_handoff_tb;
reg clk=0, rst=0; always #5 clk=~clk;
wire cmd,stop,active,lf,center,owner,fault,confirmed,pc,tx,ready; reg extstop=0;
wire [1:0] axis,mask; wire [15:0] pulse,pan,tilt; wire [3:0] state; wire [31:0] count,feedback;
gimbal1_visual_loop_guarded #(.CLOCK_HZ(1000000),.BAUD(100000),.PAN_SIGN(1),.TILT_SIGN(1)) v(
 .clk(clk),.reset_n(rst),.start(1'b0),.single_scene_confirmed(1'b1),.session_active(1'b1),.session_id(64'd1),.mcu_rx(1'b1),.motion_state(state),.motion_fault(fault),.command_ready(ready),.external_stop(extstop),.pan_target(pan),.tilt_target(tilt),.command(cmd),.axis(axis),.pulse_us(pulse),.stop_request(stop),.active(active),.fault(lf),.centered(center),.feedback_count(feedback));
zynq_motion_s1_guarded #(.CLOCK_HZ(1000000),.BAUD(100000)) m(
 .clk(clk),.reset_n(rst),.query(1'b0),.authorize(1'b0),.command(cmd),.stop_request(stop),.axis(axis),.pulse_us(pulse),.epoch(128'd1),.request_local(1'b1),.pc_quiet_ack(1'b1),.pc_rx(1'b1),.mcu_rx(1'b1),.pc_tx(pc),.mcu_tx(tx),.owner(owner),.fault(fault),.stop_confirmed(confirmed),.state(state),.accepted_count(count),.pan_target(pan),.tilt_target(tilt),.pwm_mask(mask),.command_ready(ready));
initial begin
 repeat(3) @(negedge clk);rst=1;repeat(3) @(negedge clk);
 m.owner=1;m.state=4;m.authorized=1;m.now_ms=100;m.auth_at=100;m.live_at=0;m.seq=0;m.pan_target=1500;m.tilt_target=1500;
 v.active=1;v.seen_session=1;v.dirty=1;v.latest_dx=10;v.latest_dy=0;v.received_at=v.now_ms;
 @(posedge clk);#1;
 if(m.op!==5 || state!==1 || cmd!==0 || v.pending!==1) begin $display("FAIL heartbeat arbitration");$fatal(1);end
 // Model completion of the heartbeat without waiting for an ACK; isolate handoff.
 @(negedge clk);m.state=4;m.live_at=m.now_ms;m.old_inputs[2]=0;
 @(posedge clk);#1;
 if(m.op!==2 || m.expected_pan!==1505 || v.pending!==0) begin $display("FAIL pending not accepted");$fatal(1);end
 // Explicit stop takes priority over a pending command.
 @(negedge clk);m.state=4;m.live_at=m.now_ms;m.old_inputs[2]=0;v.pending=1;extstop=1;
 @(posedge clk);#1;
 if(m.op!==2 || cmd!==0 || v.pending!==0 || !lf || !stop) begin $display("FAIL stop priority");$fatal(1);end
 // Stale pending feedback must never be sent, even when B2 is ready.
 @(negedge clk);rst=0;extstop=0;repeat(3) @(negedge clk);rst=1;repeat(3) @(negedge clk);
 m.owner=1;m.state=4;m.authorized=1;m.now_ms=10;m.auth_at=10;m.live_at=10;m.seq=0;
 v.active=1;v.seen_session=1;v.pending=1;v.received_at=0;v.now_ms=200;
 @(posedge clk);#1;
 if(m.seq!==0 || cmd!==0 || v.pending!==0 || !lf || !stop) begin $display("FAIL stale sample");$fatal(1);end
 // Reset must clear pending and never issue motion.
 @(negedge clk);rst=0;@(posedge clk);#1;
 if(cmd!==0 || v.pending!==0 || active!==0) begin $display("FAIL reset");$fatal(1);end
 $display("PASS guarded handoff, STOP, stale feedback, reset");$finish;
end
initial begin #20000;$fatal(1,"timeout");end
endmodule
