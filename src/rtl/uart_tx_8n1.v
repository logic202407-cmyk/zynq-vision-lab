`timescale 1ns/1ps
// Synchronous valid/ready UART transmitter. Stop blocks new bytes; an accepted
// byte always finishes its full stop bit unless reset is asserted.
module uart_tx_8n1 #(
    parameter integer CLOCK_HZ = 50000000,
    parameter integer BAUD = 115200
) (
    input wire clk,
    input wire reset_n,
    input wire stop,
    input wire valid,
    input wire [7:0] data,
    output wire ready,
    output wire tx,
    output reg busy,
    output reg done
);
    localparam integer DIVISOR = BAUD>0 ? (CLOCK_HZ + BAUD/2)/BAUD : 0;
    localparam CONFIG_OK = CLOCK_HZ>0 && BAUD>0 && DIVISOR>=2;
    reg [31:0] clocks;
    reg [3:0] bit_index;
    reg [9:0] frame;
    assign ready = CONFIG_OK && reset_n && !busy && !stop;
    assign tx = !reset_n || !busy ? 1'b1 : frame[bit_index];
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            clocks<=0; bit_index<=0; frame<=10'h3ff; busy<=0; done<=0;
        end else begin
            done<=0;
            if (!busy) begin
                if (valid && ready) begin
                    frame<={1'b1,data,1'b0}; busy<=1;
                    clocks<=0; bit_index<=0;
                end
            end else if (clocks==DIVISOR-1) begin
                clocks<=0;
                if (bit_index==9) begin busy<=0; done<=1; end
                else bit_index<=bit_index+1'b1;
            end else clocks<=clocks+1'b1;
        end
    end
endmodule
