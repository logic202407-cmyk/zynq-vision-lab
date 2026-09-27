`timescale 1ns / 1ps

// Candidate RGB565 red-pixel predicate. Pure combinational pixel operator.
// Thresholds match src/interface_contract.md; no camera stream is wired here.
module red_pixel_mask #(
    parameter [4:0] MIN_R5 = 5'd15,
    parameter [5:0] MAX_G6 = 6'd30,
    parameter [4:0] MAX_B5 = 5'd22
) (
    input  wire [15:0] pixel_rgb565,
    output wire        is_red
);

    wire [4:0] red5   = pixel_rgb565[15:11];
    wire [5:0] green6 = pixel_rgb565[10:5];
    wire [4:0] blue5  = pixel_rgb565[4:0];
    wire [6:0] twice_red = {1'b0, red5, 1'b0};
    wire [6:0] green_plus_margin = {1'b0, green6} + 7'd13;

    assign is_red = (red5 >= MIN_R5) &&
                    (green6 <= MAX_G6) &&
                    (blue5 <= MAX_B5) &&
                    (twice_red >= green_plus_margin) &&
                    ((blue5 >= 5'd6) || (green6 <= 6'd12));

endmodule
