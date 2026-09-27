`timescale 1ns / 1ps

// Camera-clock-domain snapshot and 32-byte UDP header extension.
// Header of video frame N contains the completed measurement for frame N-1.
// A sequence number links that measurement to the earlier video frame.
module red_result_header (
    input wire clk,
    input wire rst_n,
    input wire result_strobe,
    input wire frame_complete,
    input wire target_valid,
    input wire [18:0] red_count,
    input wire [27:0] red_sum_x,
    input wire [27:0] red_sum_y,
    input wire [9:0] red_min_x,
    input wire [8:0] red_min_y,
    input wire [9:0] red_max_x,
    input wire [8:0] red_max_y,
    input wire [5:0] header_index,
    output reg [7:0] header_byte
);
    reg [31:0] last_seq;
    reg last_complete;
    reg last_target;
    reg [18:0] last_count;
    reg [27:0] last_sum_x;
    reg [27:0] last_sum_y;
    reg [9:0] last_min_x, last_max_x;
    reg [8:0] last_min_y, last_max_y;
    wire [31:0] current_seq = last_seq + 32'd1;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            last_seq <= 32'd0;
            last_complete <= 1'b0;
            last_target <= 1'b0;
            last_count <= 19'd0;
            last_sum_x <= 28'd0;
            last_sum_y <= 28'd0;
            last_min_x <= 10'd0;
            last_min_y <= 9'd0;
            last_max_x <= 10'd0;
            last_max_y <= 9'd0;
        end else if (result_strobe) begin
            last_seq <= last_seq + 32'd1;
            last_complete <= frame_complete;
            last_target <= target_valid;
            last_count <= red_count;
            last_sum_x <= red_sum_x;
            last_sum_y <= red_sum_y;
            last_min_x <= red_min_x;
            last_min_y <= red_min_y;
            last_max_x <= red_max_x;
            last_max_y <= red_max_y;
        end
    end

    always @* begin
        case (header_index)
            6'd8:  header_byte = current_seq[31:24];
            6'd9:  header_byte = current_seq[23:16];
            6'd10: header_byte = current_seq[15:8];
            6'd11: header_byte = current_seq[7:0];
            6'd12: header_byte = last_seq[31:24];
            6'd13: header_byte = last_seq[23:16];
            6'd14: header_byte = last_seq[15:8];
            6'd15: header_byte = last_seq[7:0];
            6'd16: header_byte = {6'd0, last_target, last_complete};
            6'd17: header_byte = 8'd1; // protocol version
            6'd18, 6'd19: header_byte = 8'd0;
            6'd20: header_byte = 8'd0;
            6'd21: header_byte = {5'd0, last_count[18:16]};
            6'd22: header_byte = last_count[15:8];
            6'd23: header_byte = last_count[7:0];
            6'd24: header_byte = {4'd0, last_sum_x[27:24]};
            6'd25: header_byte = last_sum_x[23:16];
            6'd26: header_byte = last_sum_x[15:8];
            6'd27: header_byte = last_sum_x[7:0];
            6'd28: header_byte = {4'd0, last_sum_y[27:24]};
            6'd29: header_byte = last_sum_y[23:16];
            6'd30: header_byte = last_sum_y[15:8];
            6'd31: header_byte = last_sum_y[7:0];
            6'd32: header_byte = {6'd0, last_min_x[9:8]};
            6'd33: header_byte = last_min_x[7:0];
            6'd34: header_byte = {7'd0, last_min_y[8]};
            6'd35: header_byte = last_min_y[7:0];
            6'd36: header_byte = {6'd0, last_max_x[9:8]};
            6'd37: header_byte = last_max_x[7:0];
            6'd38: header_byte = {7'd0, last_max_y[8]};
            6'd39: header_byte = last_max_y[7:0];
            default: header_byte = 8'd0;
        endcase
    end
endmodule
