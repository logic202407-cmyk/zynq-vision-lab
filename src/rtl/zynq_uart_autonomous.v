`timescale 1ns/1ps
// Standalone candidate. No pin assignments, hardware access, or motion ROM.
// pc_quiet_ack is a SYSTEM contract: PC has stopped transmitting and must stay
// stopped throughout ownership handoff. No UART-only mux can guarantee this.
module zynq_uart_autonomous #(
    parameter integer CLOCK_HZ=50000000,
    parameter integer BAUD=115200,
    parameter integer DEBOUNCE_CYCLES=500000,
    parameter integer RESPONSE_CYCLES=25000000
) (
    input wire clk, reset_n,
    input wire start, command_stop, request_local, pc_quiet_ack,
    input wire pc_rx, skystar_rx,
    output wire pc_tx, skystar_tx,
    output reg local_owner,
    output wire busy, tx_busy,
    output reg tx_done, done, timeout, response_error, rejected,
    output wire [7:0] rx_data,
    output wire rx_valid, rx_frame_error,
    output wire [1:0] phase
);
    localparam integer DIV=BAUD>0 ? (CLOCK_HZ+BAUD/2)/BAUD : 0;
    localparam OK=CLOCK_HZ>0 && BAUD>0 && DIV>=8 &&
                  DEBOUNCE_CYCLES>0 && RESPONSE_CYCLES>0;
    localparam IDLE=0, SEND=1, WAIT_REPLY=2;
    reg [1:0] state;
    (* ASYNC_REG="TRUE" *) reg start_meta, start_sync;
    (* ASYNC_REG="TRUE" *) reg mode_meta, mode_sync, ack_meta, ack_sync;
    (* ASYNC_REG="TRUE" *) reg cmd_meta, cmd_sync, pc_meta, pc_sync;
    reg armed_trigger;
    reg [31:0] low_count, high_count, idle_count, response_count;
    reg [2:0] index;
    reg selected_stop, waiting_byte;
    wire byte_ready, byte_done, local_tx, rx_busy, pc_busy;
    wire [7:0] unused_data;
    wire unused_valid, unused_error;
    wire trigger_event=armed_trigger && start_sync && high_count==DEBOUNCE_CYCLES-1;
    wire byte_valid=state==SEND && !waiting_byte;
    wire last_byte=selected_stop ? index==5 : index==3;
    reg [7:0] byte_data;
    assign phase=state;
    assign busy=state!=IDLE;
    assign pc_tx=skystar_rx;
    assign skystar_tx=!reset_n ? 1'b1 : (local_owner ? local_tx : pc_rx);
    always @* begin
        byte_data=8'h0a;
        case(index)
            0: byte_data="s";
            1: byte_data="t";
            2: byte_data=selected_stop ? "o" : 8'h0d;
            3: byte_data=selected_stop ? "p" : 8'h0a;
            4: byte_data=8'h0d;
            default: byte_data=8'h0a;
        endcase
    end
    uart_tx_8n1 #(.CLOCK_HZ(CLOCK_HZ),.BAUD(BAUD)) transmitter(
        .clk(clk),.reset_n(reset_n),.stop(1'b0),.valid(byte_valid),
        .data(byte_data),.ready(byte_ready),.tx(local_tx),.busy(tx_busy),.done(byte_done));
    uart_rx #(.CLOCK_HZ(CLOCK_HZ),.BAUD(BAUD)) receiver(
        .clk(clk),.reset_n(reset_n),.rx(skystar_rx),.data(rx_data),
        .valid(rx_valid),.frame_error(rx_frame_error),.busy(rx_busy));
    uart_rx #(.CLOCK_HZ(CLOCK_HZ),.BAUD(BAUD)) pc_monitor(
        .clk(clk),.reset_n(reset_n),.rx(pc_rx),.data(unused_data),
        .valid(unused_valid),.frame_error(unused_error),.busy(pc_busy));
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            start_meta<=1; start_sync<=1; mode_meta<=0; mode_sync<=0;
            ack_meta<=0; ack_sync<=0; cmd_meta<=0; cmd_sync<=0;
            pc_meta<=1; pc_sync<=1;
        end else begin
            start_meta<=start; start_sync<=start_meta;
            mode_meta<=request_local; mode_sync<=mode_meta;
            ack_meta<=pc_quiet_ack; ack_sync<=ack_meta;
            cmd_meta<=command_stop; cmd_sync<=cmd_meta;
            pc_meta<=pc_rx; pc_sync<=pc_meta;
        end
    end
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            state<=IDLE; local_owner<=0; armed_trigger<=0;
            low_count<=0; high_count<=0; idle_count<=0; response_count<=0;
            index<=0; selected_stop<=0; waiting_byte<=0;
            tx_done<=0; done<=0; timeout<=0; response_error<=0; rejected<=0;
        end else begin
            tx_done<=0; done<=0; rejected<=0;
            // Both stable release AND stable press required. Held high on boot
            // cannot fire; busy-time events are discarded, never queued.
            if (!start_sync) begin
                high_count<=0;
                if (low_count<DEBOUNCE_CYCLES) low_count<=low_count+1'b1;
                if (low_count==DEBOUNCE_CYCLES-1) armed_trigger<=1;
            end else begin
                low_count<=0;
                if (high_count<DEBOUNCE_CYCLES) high_count<=high_count+1'b1;
                if (trigger_event) armed_trigger<=0;
            end
            if (!pc_sync || !pc_rx || !local_tx || pc_busy || tx_busy ||
                rx_busy || !skystar_rx || !ack_sync || !pc_quiet_ack)
                idle_count<=0;
            else if (idle_count<12*DIV) idle_count<=idle_count+1'b1;
            if (OK && state==IDLE && !trigger_event && !start_sync &&
                idle_count==12*DIV && pc_rx && pc_sync && pc_meta &&
                pc_quiet_ack && ack_sync && !pc_busy && !rx_busy)
                local_owner<=mode_sync;
            if (trigger_event) begin
                if (!OK || state!=IDLE || !local_owner || !mode_sync) rejected<=1;
                else begin
                    state<=SEND; index<=0; selected_stop<=cmd_sync;
                    waiting_byte<=0; timeout<=0; response_error<=0;
                end
            end
            if (state==SEND) begin
                if (byte_valid && byte_ready) waiting_byte<=1;
                if (byte_done) begin
                    waiting_byte<=0;
                    if (last_byte) begin
                        state<=WAIT_REPLY; tx_done<=1; response_count<=0;
                    end else index<=index+1'b1;
                end
            end
            if (state==WAIT_REPLY) begin
                // A received LF is a line boundary, NOT a semantic command ACK.
                // Periodic MCU telemetry can also satisfy this condition.
                if (rx_frame_error) begin
                    response_error<=1; state<=IDLE; done<=1;
                end else if (rx_valid && rx_data==8'h0a) begin state<=IDLE; done<=1; end
                else if (response_count==RESPONSE_CYCLES-1) begin
                    timeout<=1; state<=IDLE; done<=1;
                end else response_count<=response_count+1'b1;
            end
        end
    end
endmodule
