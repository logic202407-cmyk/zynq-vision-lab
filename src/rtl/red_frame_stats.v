`timescale 1ns / 1ps

// Frame-atomic red-pixel statistics for a row-major RGB565 pixel stream.
// The caller supplies coordinates and marks the first/last pixel of each frame.
// No division is performed in PL: the host computes floor(sum/count).
module red_frame_stats #(
    parameter integer WIDTH = 640,
    parameter integer HEIGHT = 480
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        pixel_valid,
    input  wire        frame_start,
    input  wire        frame_end,
    input  wire [15:0] pixel_rgb565,
    input  wire [9:0]  pixel_x,
    input  wire [8:0]  pixel_y,
    output reg         result_strobe,
    output reg         frame_complete,
    output reg         target_valid,
    output reg  [18:0] red_count,
    output reg  [27:0] red_sum_x,
    output reg  [27:0] red_sum_y,
    output reg  [9:0]  red_min_x,
    output reg  [8:0]  red_min_y,
    output reg  [9:0]  red_max_x,
    output reg  [8:0]  red_max_y
);
    localparam integer FRAME_PIXELS = WIDTH * HEIGHT;

    wire is_red;
    red_pixel_mask u_red_pixel_mask (
        .pixel_rgb565(pixel_rgb565),
        .is_red(is_red)
    );

    reg active;
    reg [18:0] pixel_total;
    reg [18:0] count_acc;
    reg [27:0] sum_x_acc;
    reg [27:0] sum_y_acc;
    reg [9:0] min_x_acc;
    reg [8:0] min_y_acc;
    reg [9:0] max_x_acc;
    reg [8:0] max_y_acc;

    wire accept_pixel = pixel_valid && (frame_start || active);
    wire red_hit = accept_pixel && is_red;
    wire [18:0] base_total = frame_start ? 19'd0 : pixel_total;
    wire [18:0] base_count = frame_start ? 19'd0 : count_acc;
    wire [27:0] base_sum_x = frame_start ? 28'd0 : sum_x_acc;
    wire [27:0] base_sum_y = frame_start ? 28'd0 : sum_y_acc;
    wire [9:0] base_min_x = frame_start ? 10'h3ff : min_x_acc;
    wire [8:0] base_min_y = frame_start ? 9'h1ff : min_y_acc;
    wire [9:0] base_max_x = frame_start ? 10'd0 : max_x_acc;
    wire [8:0] base_max_y = frame_start ? 9'd0 : max_y_acc;

    // Saturating count preserves an incomplete-frame verdict on extra pixels.
    wire [18:0] next_total =
        (base_total <= FRAME_PIXELS) ? base_total + 19'd1 : base_total;
    wire [18:0] next_count = base_count + (red_hit ? 19'd1 : 19'd0);
    wire [27:0] next_sum_x = base_sum_x + (red_hit ? {18'd0, pixel_x} : 28'd0);
    wire [27:0] next_sum_y = base_sum_y + (red_hit ? {19'd0, pixel_y} : 28'd0);
    wire [9:0] next_min_x = red_hit && (pixel_x < base_min_x) ? pixel_x : base_min_x;
    wire [8:0] next_min_y = red_hit && (pixel_y < base_min_y) ? pixel_y : base_min_y;
    wire [9:0] next_max_x = red_hit && (pixel_x > base_max_x) ? pixel_x : base_max_x;
    wire [8:0] next_max_y = red_hit && (pixel_y > base_max_y) ? pixel_y : base_max_y;
    wire complete_now = (next_total == FRAME_PIXELS) &&
                        (pixel_x == WIDTH - 1) && (pixel_y == HEIGHT - 1);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0;
            pixel_total <= 19'd0;
            count_acc <= 19'd0;
            sum_x_acc <= 28'd0;
            sum_y_acc <= 28'd0;
            min_x_acc <= 10'h3ff;
            min_y_acc <= 9'h1ff;
            max_x_acc <= 10'd0;
            max_y_acc <= 9'd0;
            result_strobe <= 1'b0;
            frame_complete <= 1'b0;
            target_valid <= 1'b0;
            red_count <= 19'd0;
            red_sum_x <= 28'd0;
            red_sum_y <= 28'd0;
            red_min_x <= 10'd0;
            red_min_y <= 9'd0;
            red_max_x <= 10'd0;
            red_max_y <= 9'd0;
        end else begin
            result_strobe <= 1'b0;
            if (accept_pixel) begin
                active <= !frame_end;
                pixel_total <= next_total;
                count_acc <= next_count;
                sum_x_acc <= next_sum_x;
                sum_y_acc <= next_sum_y;
                min_x_acc <= next_min_x;
                min_y_acc <= next_min_y;
                max_x_acc <= next_max_x;
                max_y_acc <= next_max_y;
                if (frame_end) begin
                    result_strobe <= 1'b1;
                    frame_complete <= complete_now;
                    target_valid <= complete_now && (next_count != 19'd0);
                    red_count <= complete_now ? next_count : 19'd0;
                    red_sum_x <= complete_now ? next_sum_x : 28'd0;
                    red_sum_y <= complete_now ? next_sum_y : 28'd0;
                    red_min_x <= complete_now && next_count != 19'd0 ? next_min_x : 10'd0;
                    red_min_y <= complete_now && next_count != 19'd0 ? next_min_y : 9'd0;
                    red_max_x <= complete_now && next_count != 19'd0 ? next_max_x : 10'd0;
                    red_max_y <= complete_now && next_count != 19'd0 ? next_max_y : 9'd0;
                end
            end
        end
    end
endmodule
