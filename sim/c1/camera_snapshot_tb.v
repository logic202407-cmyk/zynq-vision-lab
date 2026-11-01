`timescale 1ns/1ps
module camera_snapshot_tb;
reg clk=0,rst=0,rv=0,target=1;always #7 clk=~clk;
wire valid;wire[218:0] snap;wire[31:0] seq,tick;
camera_measurement_snapshot dut(clk,rst,rv,1'b1,target,19'd2,28'd60,28'd80,10'd10,10'd50,9'd20,9'd60,valid,snap,seq,tick);
task result;begin @(negedge clk);rv=1;@(negedge clk);rv=0;end endtask
initial begin
#20;rst=1;result;if(seq!=1||valid)$fatal(1,"first should decimate");
result;if(seq!=2||valid)$fatal(1,"second should decimate");
result;if(!valid||seq!=3||snap!={8'd2,16'd640,16'd480,32'd3,tick-32'd1,1'b1,1'b1,19'd2,28'd60,28'd80,10'd10,9'd20,10'd50,9'd60})$fatal(1,"snapshot field/phase mismatch");
@(negedge clk);if(valid)$fatal(1,"strobe must be one cycle");
target=0;result;result;result;if(!valid||snap[113]||snap[178:147]!=6)$fatal(1,"no-target must propagate");
rst=0;#1;if(seq||valid||snap)$fatal(1,"reset retained data");
#20;rst=1;result;result;result;if(snap[178:147]!=3)$fatal(1,"reset counter restart");
$display("CAMERA_SNAPSHOT_PASS 7");$finish;
end
initial begin #10000;$fatal(1,"watchdog");end
endmodule
