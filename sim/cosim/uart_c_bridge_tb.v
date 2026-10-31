`timescale 1ns/1ps
// Only testbench inputs are driven through XSI. DUT internals are never forced.
module uart_c_bridge_tb(input wire mcu_rx, output wire [104:0] bridge_sample);
    reg clk=0,reset_n=0,start=0,command_stop=0;
    always #5 clk=~clk;
    wire fpga_tx,pc_tx,owner,busy,tx_busy,tx_done,done,timeout,error,rejected;
    wire [7:0] rx_data;
    wire rx_valid,rx_error;
    wire [1:0] phase;
    reg [31:0] rx_count=0,err_count=0,done_count=0;
    reg [7:0] last_rx=0;
    assign bridge_sample={rx_count,last_rx,err_count,done_count,fpga_tx};
    zynq_uart_autonomous #(.CLOCK_HZ(100000000),.DEBOUNCE_CYCLES(8),
        .RESPONSE_CYCLES(10000000)) dut(
        clk,reset_n,start,command_stop,1'b1,1'b1,1'b1,mcu_rx,pc_tx,fpga_tx,
        owner,busy,tx_busy,tx_done,done,timeout,error,rejected,
        rx_data,rx_valid,rx_error,phase);
    always @(posedge clk) if(reset_n) begin
        if(rx_valid) begin rx_count<=rx_count+1;last_rx<=rx_data;end
        if(rx_error) err_count<=err_count+1;
        if(done) done_count<=done_count+1;
    end
    initial begin
        #100;reset_n=1;
        #10000000; wait(owner && !busy); start=1;#1000;start=0;
        #45000000;command_stop=1;start=1;#1000;start=0;
    end
    initial begin #200000000; $fatal(1,"cosim watchdog"); end
endmodule
