`timescale 1ns / 1ps

// Causal 3x3 binary majority: the arriving (x,y) completes the window
// centered on (x-1,y-1). Outer image borders are deliberately excluded.
// Two one-bit line memories are overwritten before y>=2; no RAM reset is
// needed. Idle cycles do not advance either the line or column histories.
module red_mask_majority3x3 #(
    parameter integer WIDTH = 640
) (
    input wire clk,
    input wire rst_n,
    input wire pixel_valid,
    input wire is_red,
    input wire [9:0] pixel_x,
    input wire [8:0] pixel_y,
    output wire filtered_red
);
    (* ram_style = "distributed" *) reg line_one [0:WIDTH-1];
    (* ram_style = "distributed" *) reg line_two [0:WIDTH-1];
    reg [2:0] column_one, column_two;
    wire [2:0] column_now = pixel_x < WIDTH ?
        {line_two[pixel_x], line_one[pixel_x], is_red} : 3'b000;
    wire [3:0] votes =
        {3'd0, column_now[0]} + {3'd0, column_now[1]} + {3'd0, column_now[2]} +
        {3'd0, column_one[0]} + {3'd0, column_one[1]} + {3'd0, column_one[2]} +
        {3'd0, column_two[0]} + {3'd0, column_two[1]} + {3'd0, column_two[2]};
    assign filtered_red = pixel_valid && pixel_x >= 2 && pixel_x < WIDTH &&
                          pixel_y >= 2 && votes >= 5;

    always @(posedge clk) begin
        if (rst_n && pixel_valid && pixel_x < WIDTH) begin
            line_one[pixel_x] <= is_red;
            line_two[pixel_x] <= line_one[pixel_x];
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            column_one <= 3'd0;
            column_two <= 3'd0;
        end else if (pixel_valid && pixel_x < WIDTH) begin
            column_one <= column_now;
            column_two <= pixel_x == 0 ? 3'd0 : column_one;
        end
    end
endmodule
