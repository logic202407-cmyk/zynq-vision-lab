`timescale 1ns/1ps
module visual_runtime_direction_tb;
reg clk=0,rst=0,start=0; reg [1:0] pd=0,td=0; always #5 clk=~clk;
wire cmd,stop,active,fault,center;wire[1:0] axis;wire[15:0] pulse;wire[31:0] count;
gimbal1_visual_loop_runtime #(.CLOCK_HZ(1000000),.BAUD(100000)) dut(
 .clk(clk),.reset_n(rst),.start(start),.single_scene_confirmed(1'b1),.session_active(1'b1),
 .pan_direction(pd),.tilt_direction(td),.session_id(64'd1),.mcu_rx(1'b1),
 .motion_state(4'd4),.motion_fault(1'b0),.command_ready(1'b1),.external_stop(1'b0),
 .pan_target(16'd1500),.tilt_target(16'd1500),.command(cmd),.axis(axis),.pulse_us(pulse),
 .stop_request(stop),.active(active),.fault(fault),.centered(center),.feedback_count(count));
initial begin
 repeat(3) @(negedge clk);rst=1;repeat(3) @(negedge clk);
 start=1;@(posedge clk);#1;if(active||cmd) $fatal(1,"undefined sign enabled");
 @(negedge clk);start=0;pd=1;td=2;@(negedge clk);start=1;@(posedge clk);#1;
 if(!active||fault) $fatal(1,"valid direction refused");
 @(negedge clk);start=0;dut.dirty=1;dut.latest_dx=10;dut.latest_dy=0;dut.received_at=dut.now_ms;
 @(posedge clk);#1;if(!cmd||axis!=0||pulse!=1505)$fatal(1,"positive PAN mapping failed");
 @(posedge clk);#1;
 @(negedge clk);dut.dirty=1;dut.latest_dx=0;dut.latest_dy=10;dut.received_at=dut.now_ms;
 @(posedge clk);#1;if(!cmd||axis!=1||pulse!=1495)$fatal(1,"negative TILT mapping failed");
 @(posedge clk);#1;
 @(negedge clk);dut.pending=1;pd=2;
 #1;if(cmd)$fatal(1,"direction changed sent command");
 @(posedge clk);#1;if(!fault||!stop||active||cmd)$fatal(1,"direction change did not fault and stop");
 @(negedge clk);rst=0;@(posedge clk);#1;if(cmd||active||fault)$fatal(1,"reset failed");
 $display("PASS runtime direction disabled, mapping, change fail closed and reset");$finish;
end
initial begin #10000;$fatal(1,"timeout");end
endmodule
