`timescale 1ns/1ps
// Independent candidate, never wired into the validated bridge by default.
// request_local/trigger/query/stop are synchronous, debounced operator controls.
// Exactly one mux drives the STM32 TX wire. Ownership changes only after an
// idle guard on both streams and an idle transmitter. No motion or arm frames.
module zynq_uart_diagnostic #(
    parameter integer CLOCK_HZ = 50000000,
    parameter integer BAUD = 115200
) (
    input wire clk,
    input wire reset_n,
    input wire request_local,
    input wire trigger,
    input wire query,
    input wire stop,
    input wire pc_tx_line,
    input wire skystar_rx_line,
    output wire skystar_tx_line,
    output wire pc_rx_line,
    output reg local_owner,
    output reg busy,
    output reg done,
    output reg aborted,
    output reg rejected
);
    localparam integer DIVISOR = BAUD>0 ? (CLOCK_HZ + BAUD/2)/BAUD : 0;
    localparam CONFIG_OK = CLOCK_HZ>0 && BAUD>0 && DIVISOR>=2;
    localparam integer IDLE_GUARD = 12*DIVISOR;
    reg pc_meta, pc_sync, trigger_old;
    reg [31:0] idle_clocks;
    reg [3:0] index;
    reg message_query, waiting_byte, stop_pending;
    wire byte_ready, byte_busy, byte_done, local_tx;
    wire rising_trigger = trigger && !trigger_old;
    wire send_byte = busy && !waiting_byte && !stop_pending && !stop;
    reg [7:0] byte_data;
    wire last_byte = message_query ? index==2 : index==8;
    assign pc_rx_line = skystar_rx_line;
    assign skystar_tx_line = !reset_n ? 1'b1 : (local_owner ? local_tx : pc_tx_line);
    always @* begin
        byte_data=8'h0a;
        if (message_query) begin
            case(index) 0:byte_data="s"; 1:byte_data="t"; default:byte_data=8'h0a; endcase
        end else begin
            case(index)
                0,1,6,7:byte_data="_";
                2:byte_data="d"; 3:byte_data="i";
                4:byte_data="a"; 5:byte_data="g";
                default:byte_data=8'h0a;
            endcase
        end
    end
    uart_tx_8n1 #(.CLOCK_HZ(CLOCK_HZ),.BAUD(BAUD)) transmitter (
        .clk(clk),.reset_n(reset_n),.stop(stop || stop_pending),
        .valid(send_byte),.data(byte_data),.ready(byte_ready),.tx(local_tx),
        .busy(byte_busy),.done(byte_done)
    );
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            pc_meta<=1; pc_sync<=1; idle_clocks<=0; trigger_old<=1;
            local_owner<=0; busy<=0; done<=0; aborted<=0; rejected<=0;
            index<=0; message_query<=1; waiting_byte<=0; stop_pending<=0;
        end else begin
            pc_meta<=pc_tx_line; pc_sync<=pc_meta; trigger_old<=trigger;
            done<=0; rejected<=0;
            if (!pc_sync || !local_tx) idle_clocks<=0;
            else if (idle_clocks<IDLE_GUARD) idle_clocks<=idle_clocks+1'b1;
            if (CONFIG_OK && !busy && !byte_busy && !trigger && pc_tx_line && pc_meta && pc_sync &&
                idle_clocks==IDLE_GUARD)
                local_owner<=request_local;
            if (rising_trigger) begin
                if (!CONFIG_OK || busy || !local_owner || !request_local || stop) rejected<=1;
                else begin
                    busy<=1; aborted<=0; index<=0; waiting_byte<=0;
                    stop_pending<=0; message_query<=query;
                end
            end
            if (busy) begin
                if (stop) stop_pending<=1;
                if (send_byte && byte_ready) waiting_byte<=1;
                if (byte_done) begin
                    waiting_byte<=0;
                    if (last_byte || stop_pending || stop) begin
                        busy<=0; done<=1; aborted<=stop_pending || stop;
                    end else index<=index+1'b1;
                end else if ((stop_pending || stop) && !byte_busy && !waiting_byte) begin
                    busy<=0; done<=1; aborted<=1;
                end
            end
        end
    end
endmodule
