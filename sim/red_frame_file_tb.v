`timescale 1ns / 1ps

// Drive exactly one 640x480 frame from a caller-supplied RGB565 hex file.
// The runner compares the printed PL fields with the Python reference for
// the same bytes. Hex file contents may be private and stay outside Git.
module red_frame_file_tb;
    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg rst_n = 1'b0;
    reg pixel_valid = 1'b0;
    reg frame_start = 1'b0;
    reg frame_end = 1'b0;
    reg [15:0] pixel_rgb565 = 16'd0;
    reg [9:0] pixel_x = 10'd0;
    reg [8:0] pixel_y = 9'd0;
    wire result_strobe, frame_complete, target_valid;
    wire [18:0] red_count;
    wire [27:0] red_sum_x, red_sum_y;
    wire [9:0] red_min_x, red_max_x;
    wire [8:0] red_min_y, red_max_y;
    reg [15:0] pixels [0:307199];
    integer i;

    red_frame_stats dut (
        .clk(clk), .rst_n(rst_n), .pixel_valid(pixel_valid),
        .frame_start(frame_start), .frame_end(frame_end),
        .pixel_rgb565(pixel_rgb565), .pixel_x(pixel_x), .pixel_y(pixel_y),
        .result_strobe(result_strobe), .frame_complete(frame_complete),
        .target_valid(target_valid), .red_count(red_count),
        .red_sum_x(red_sum_x), .red_sum_y(red_sum_y),
        .red_min_x(red_min_x), .red_min_y(red_min_y),
        .red_max_x(red_max_x), .red_max_y(red_max_y)
    );

    initial begin
        $readmemh("frame.mem", pixels);
        repeat (2) @(negedge clk);
        rst_n = 1'b1;
        for (i = 0; i < 307200; i = i + 1) begin
            @(negedge clk);
            pixel_valid = 1'b1;
            pixel_rgb565 = pixels[i];
            pixel_x = i % 640;
            pixel_y = i / 640;
            frame_start = (i == 0);
            frame_end = (i == 307199);
        end
        @(posedge clk);
        #1;
        if (result_strobe !== 1'b1 || frame_complete !== 1'b1)
            $fatal(1, "PL did not accept a complete frame");
        $display("FRAME_RESULT valid=%0d count=%0d sx=%0d sy=%0d minx=%0d miny=%0d maxx=%0d maxy=%0d",
                 target_valid, red_count, red_sum_x, red_sum_y,
                 red_min_x, red_min_y, red_max_x, red_max_y);
        $finish;
    end
endmodule
