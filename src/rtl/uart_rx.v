`timescale 1ns/1ps
// 8N1 center-sampling receiver. A bad stop bit waits for idle before rearming.
module uart_rx #(
    parameter integer CLOCK_HZ=50000000,
    parameter integer BAUD=115200
) (
    input wire clk, reset_n, rx,
    output reg [7:0] data,
    output reg valid, frame_error,
    output wire busy
);
    localparam integer DIV=BAUD>0 ? (CLOCK_HZ+BAUD/2)/BAUD : 0;
    localparam OK=CLOCK_HZ>0 && BAUD>0 && DIV>=8;
    localparam IDLE=0, START=1, DATA=2, STOP=3, RECOVER=4;
    (* ASYNC_REG="TRUE" *) reg meta, synced;
    reg [2:0] state, bit_index;
    reg [31:0] ticks;
    reg [7:0] shift;
    assign busy=state!=IDLE;
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin meta<=1; synced<=1; end
        else begin meta<=rx; synced<=meta; end
    end
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            state<=IDLE; ticks<=0; bit_index<=0; shift<=0;
            data<=0; valid<=0; frame_error<=0;
        end else begin
            valid<=0; frame_error<=0;
            case(state)
                IDLE: if (OK && !synced) begin state<=START; ticks<=DIV/2-1; end
                START: if (ticks!=0) ticks<=ticks-1;
                    else if (synced) state<=IDLE;
                    else begin state<=DATA; ticks<=DIV-1; bit_index<=0; end
                DATA: if (ticks!=0) ticks<=ticks-1;
                    else begin
                        shift[bit_index]<=synced; ticks<=DIV-1;
                        if (bit_index==7) state<=STOP;
                        else bit_index<=bit_index+1'b1;
                    end
                STOP: if (ticks!=0) ticks<=ticks-1;
                    else if (synced) begin data<=shift; valid<=1; state<=IDLE; end
                    else begin frame_error<=1; state<=RECOVER; ticks<=0; end
                RECOVER: if (!synced) ticks<=0;
                    else if (ticks==DIV-1) begin state<=IDLE; ticks<=0; end
                    else ticks<=ticks+1'b1;
                default: state<=IDLE;
            endcase
        end
    end
endmodule
