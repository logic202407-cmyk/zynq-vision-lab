`timescale 1ns/1ps
// Functional-netlist smoke: independently decode the actual synthesized TX pin.
module motion_netlist_tb;
 reg clk=0,reset_n=0,query=0;
 wire tx,pc_tx,owner,fault,stopped;wire [3:0] state;
 wire [31:0] accepted;wire [15:0] pan,tilt;wire [1:0] mask;
 localparam BIT=8680;
 localparam [359:0] EXPECTED={"s1q 00000000000000000000000012345678 st*ba0d",8'h0a};
 integer i,j;reg [7:0] b;
 always #5 clk=~clk;
 zynq_motion_s1 dut(.clk(clk),.reset_n(reset_n),.query(query),.authorize(1'b0),
 .command(1'b0),.stop_request(1'b0),.axis(2'b0),.pulse_us(16'd1500),
 .epoch(128'h12345678),.request_local(1'b1),.pc_quiet_ack(1'b1),.pc_rx(1'b1),.mcu_rx(1'b1),
 .pc_tx(pc_tx),.mcu_tx(tx),.owner(owner),.fault(fault),.stop_confirmed(stopped),
 .state(state),.accepted_count(accepted),.pan_target(pan),.tilt_target(tilt),.pwm_mask(mask));
 initial begin #200;reset_n=1;#200000;if(!owner) $fatal(1,"no ownership");query=1;#100;query=0;end
 initial begin
 for(i=0;i<45;i=i+1) begin
 @(negedge tx);#(BIT+BIT/2);b=0;
 for(j=0;j<8;j=j+1) begin b[j]=tx;#BIT;end
 if(tx!==1'b1) $fatal(1,"bad stop bit");
 if(b!==EXPECTED[359-i*8 -:8]) $fatal(1,"byte %0d got %02x expected %02x",i,b,EXPECTED[359-i*8 -:8]);
 end
 #10000;
 if(state!=2||fault||accepted!=0||mask!=0) $fatal(1,"unexpected terminal state");
 $display("MOTION_NETLIST_PASS 45 exact UART bytes and safe query-only state");$finish;
 end
 initial begin #10000000;$fatal(1,"netlist watchdog");end
endmodule
