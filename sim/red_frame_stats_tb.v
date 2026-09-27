`timescale 1ns / 1ps

module red_frame_stats_tb;
    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg rst_n = 1'b0;
    reg pixel_valid = 1'b0;
    reg frame_start = 1'b0;
    reg frame_end = 1'b0;
    reg [15:0] pixel_rgb565 = 16'd0;
    reg [9:0] pixel_x = 10'd0;
    reg [8:0] pixel_y = 9'd0;
    wire result_strobe;
    wire frame_complete;
    wire target_valid;
    wire [18:0] red_count;
    wire [27:0] red_sum_x;
    wire [27:0] red_sum_y;
    wire [9:0] red_min_x;
    wire [8:0] red_min_y;
    wire [9:0] red_max_x;
    wire [8:0] red_max_y;
    integer failures = 0;
    integer x;
    integer y;

    red_frame_stats #(.WIDTH(4), .HEIGHT(3)) dut (
        .clk(clk), .rst_n(rst_n), .pixel_valid(pixel_valid),
        .frame_start(frame_start), .frame_end(frame_end),
        .pixel_rgb565(pixel_rgb565), .pixel_x(pixel_x), .pixel_y(pixel_y),
        .result_strobe(result_strobe), .frame_complete(frame_complete),
        .target_valid(target_valid), .red_count(red_count),
        .red_sum_x(red_sum_x), .red_sum_y(red_sum_y),
        .red_min_x(red_min_x), .red_min_y(red_min_y),
        .red_max_x(red_max_x), .red_max_y(red_max_y)
    );

    task send_pixel;
        input [9:0] px;
        input [8:0] py;
        input [15:0] color;
        input sof;
        input eof;
        begin
            @(negedge clk);
            pixel_valid = 1'b1;
            pixel_x = px;
            pixel_y = py;
            pixel_rgb565 = color;
            frame_start = sof;
            frame_end = eof;
            @(posedge clk);
            #1;
        end
    endtask

    task gap;
        begin
            @(negedge clk);
            pixel_valid = 1'b0;
            frame_start = 1'b0;
            frame_end = 1'b0;
            @(posedge clk);
            #1;
            if (result_strobe !== 1'b0)
                failures = failures + 1;
        end
    endtask

    task check_result;
        input complete;
        input target;
        input [18:0] count;
        input [27:0] sx;
        input [27:0] sy;
        input [9:0] minx;
        input [8:0] miny;
        input [9:0] maxx;
        input [8:0] maxy;
        begin
            if (result_strobe !== 1'b1 || frame_complete !== complete ||
                target_valid !== target || red_count !== count ||
                red_sum_x !== sx || red_sum_y !== sy ||
                red_min_x !== minx || red_min_y !== miny ||
                red_max_x !== maxx || red_max_y !== maxy) begin
                $display("FAIL result complete=%b target=%b count=%0d sum=(%0d,%0d) box=(%0d,%0d,%0d,%0d)",
                         frame_complete, target_valid, red_count, red_sum_x,
                         red_sum_y, red_min_x, red_min_y, red_max_x, red_max_y);
                failures = failures + 1;
            end
        end
    endtask

    initial begin
        repeat (2) @(negedge clk);
        rst_n = 1'b1;
        // Four red pixels, including the final pixel; idle gaps must not count.
        for (y = 0; y < 3; y = y + 1) begin
            for (x = 0; x < 4; x = x + 1) begin
                send_pixel(x, y,
                    ((x == 0 && y == 0) || (x == 3 && y == 0) ||
                     (x == 1 && y == 1) || (x == 3 && y == 2)) ? 16'hf800 : 16'h0000,
                    x == 0 && y == 0, x == 3 && y == 2);
                if (x == 1 && y == 1) gap();
            end
        end
        check_result(1'b1, 1'b1, 19'd4, 28'd7, 28'd3,
                     10'd0, 9'd0, 10'd3, 9'd2);
        gap();
        // A complete frame with no target must clear all previous measurements.
        for (y = 0; y < 3; y = y + 1)
            for (x = 0; x < 4; x = x + 1)
                send_pixel(x, y, 16'h07e0, x == 0 && y == 0, x == 3 && y == 2);
        check_result(1'b1, 1'b0, 19'd0, 28'd0, 28'd0,
                     10'd0, 9'd0, 10'd0, 9'd0);
        gap();
        // Ending after only three pixels must produce an invalid snapshot.
        send_pixel(0, 0, 16'hf800, 1'b1, 1'b0);
        send_pixel(1, 0, 16'hf800, 1'b0, 1'b0);
        send_pixel(3, 2, 16'hf800, 1'b0, 1'b1);
        check_result(1'b0, 1'b0, 19'd0, 28'd0, 28'd0,
                     10'd0, 9'd0, 10'd0, 9'd0);
        gap();
        // A new start must discard any partial frame accumulated before it.
        send_pixel(0, 0, 16'hf800, 1'b1, 1'b0);
        send_pixel(1, 0, 16'hf800, 1'b0, 1'b0);
        for (y = 0; y < 3; y = y + 1)
            for (x = 0; x < 4; x = x + 1)
                send_pixel(x, y, (x == 2 && y == 1) ? 16'hf800 : 16'h0000,
                           x == 0 && y == 0, x == 3 && y == 2);
        check_result(1'b1, 1'b1, 19'd1, 28'd2, 28'd1,
                     10'd2, 9'd1, 10'd2, 9'd1);

        if (failures == 0)
            $display("RED_FRAME_STATS_TB_PASS");
        else
            $fatal(1, "RED_FRAME_STATS_TB_FAIL count=%0d", failures);
        $finish;
    end
endmodule
