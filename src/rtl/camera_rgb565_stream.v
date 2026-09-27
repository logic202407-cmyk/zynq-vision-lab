`timescale 1ns / 1ps

// Parallel monitor for the vendor OV5640 8-bit DVP stream. HREF carries
// big-endian RGB565 bytes; VSYNC high resets the frame row counter. This module
// does not modify or delay the camera bytes delivered to the video packetizer.
module camera_rgb565_stream #(
    parameter integer WIDTH = 640,
    parameter integer HEIGHT = 480
) (
    input  wire        cam_pclk,
    input  wire        rst_n,
    input  wire        cam_vsync,
    input  wire        cam_href,
    input  wire [7:0]  cam_data,
    output reg         pixel_valid,
    output reg         frame_start,
    output reg         frame_end,
    output reg  [15:0] pixel_rgb565,
    output reg  [9:0]  pixel_x,
    output reg  [8:0]  pixel_y
);
    reg seen_vsync;
    reg href_d;
    reg [8:0] row;
    reg [10:0] byte_count;
    reg [7:0] high_byte;

    always @(posedge cam_pclk or negedge rst_n) begin
        if (!rst_n) begin
            seen_vsync <= 1'b0;
            href_d <= 1'b0;
            row <= 9'd0;
            byte_count <= 11'd0;
            high_byte <= 8'd0;
            pixel_valid <= 1'b0;
            frame_start <= 1'b0;
            frame_end <= 1'b0;
            pixel_rgb565 <= 16'd0;
            pixel_x <= 10'd0;
            pixel_y <= 9'd0;
        end else begin
            href_d <= cam_href;
            pixel_valid <= 1'b0;
            frame_start <= 1'b0;
            frame_end <= 1'b0;
            if (cam_vsync) begin
                seen_vsync <= 1'b1;
                row <= 9'd0;
                byte_count <= 11'd0;
            end else if (cam_href) begin
                if (byte_count < WIDTH * 2) begin
                    byte_count <= byte_count + 11'd1;
                    if (!byte_count[0]) begin
                        high_byte <= cam_data;
                    end else if (seen_vsync && row < HEIGHT) begin
                        pixel_valid <= 1'b1;
                        pixel_rgb565 <= {high_byte, cam_data};
                        pixel_x <= byte_count[10:1];
                        pixel_y <= row;
                        frame_start <= (row == 0 && byte_count == 11'd1);
                        frame_end <= (row == HEIGHT - 1 && byte_count == WIDTH * 2 - 1);
                    end
                end
            end else begin
                byte_count <= 11'd0;
                if (href_d && row < HEIGHT)
                    row <= row + 9'd1;
            end
        end
    end
endmodule
