`timescale 1ns / 1ps

module red_spatial_stats_tb;
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0;
    reg pixel_valid = 0, frame_start = 0, frame_end = 0;
    reg [15:0] pixel_rgb565 = 0;
    reg [9:0] pixel_x = 0;
    reg [8:0] pixel_y = 0;
    wire result_strobe, frame_complete, target_valid;
    wire [18:0] red_count;
    wire [27:0] red_sum_x, red_sum_y;
    wire [9:0] red_min_x, red_max_x;
    wire [8:0] red_min_y, red_max_y;
    integer x, y, scene;

    red_frame_stats #(.WIDTH(6), .HEIGHT(6), .SPATIAL_FILTER(1)) dut (
        .clk(clk), .rst_n(rst_n), .pixel_valid(pixel_valid),
        .frame_start(frame_start), .frame_end(frame_end),
        .pixel_rgb565(pixel_rgb565), .pixel_x(pixel_x), .pixel_y(pixel_y),
        .result_strobe(result_strobe), .frame_complete(frame_complete),
        .target_valid(target_valid), .red_count(red_count),
        .red_sum_x(red_sum_x), .red_sum_y(red_sum_y),
        .red_min_x(red_min_x), .red_min_y(red_min_y),
        .red_max_x(red_max_x), .red_max_y(red_max_y)
    );

    task drive_scene;
        input integer kind;
        begin
            for (y = 0; y < 6; y = y + 1) begin
                for (x = 0; x < 6; x = x + 1) begin
                    @(negedge clk);
                    pixel_valid = 1;
                    pixel_x = x;
                    pixel_y = y;
                    frame_start = (x == 0 && y == 0);
                    frame_end = (x == 5 && y == 5);
                    pixel_rgb565 = 0;
                    if (kind == 1 ||
                        (kind == 2 && ((x >= 2 && x <= 4 && y >= 2 && y <= 4) ||
                                      (x == 0 && y == 0))) ||
                        (kind >= 3 && ((y == 2 && x >= 2 && x <= 4) ||
                                       (y == 3 && x == 2) ||
                                       (kind == 4 && y == 3 && x == 3))))
                        pixel_rgb565 = 16'hf800;
                    if (!frame_end) begin
                        @(negedge clk);
                        pixel_valid = 0;
                        frame_start = 0;
                        repeat (x % 3) @(negedge clk);
                    end
                end
            end
            @(posedge clk); #1;
            if (!result_strobe || !frame_complete)
                $fatal(1, "missing complete spatial result");
            if ((kind == 0 || kind == 3) &&
                (target_valid || red_count || red_sum_x || red_sum_y))
                $fatal(1, "empty frame leaked earlier line memory");
            if (kind == 1 && (!target_valid || red_count != 16 ||
                             red_sum_x != 40 || red_sum_y != 40 ||
                             red_min_x != 1 || red_min_y != 1 ||
                             red_max_x != 4 || red_max_y != 4))
                $fatal(1, "all-red border or coordinate mismatch");
            if (kind == 2 && (!target_valid || red_count != 5 ||
                             red_sum_x != 15 || red_sum_y != 15 ||
                             red_min_x != 2 || red_min_y != 2 ||
                             red_max_x != 4 || red_max_y != 4))
                $fatal(1, "isolated speck or patch mismatch");
            if (kind == 4 && (!target_valid || red_count != 2 ||
                             red_sum_x != 6 || red_sum_y != 5 ||
                             red_min_x != 3 || red_min_y != 2 ||
                             red_max_x != 3 || red_max_y != 3))
                $fatal(1, "five-vote threshold mismatch");
            @(negedge clk);
            pixel_valid = 0; frame_start = 0; frame_end = 0;
        end
    endtask

    initial begin
        repeat (2) @(negedge clk);
        rst_n = 1;
        drive_scene(1);
        drive_scene(0);
        drive_scene(2);
        drive_scene(3);
        drive_scene(4);
        rst_n = 0;
        repeat (2) @(negedge clk);
        rst_n = 1;
        drive_scene(0);
        drive_scene(1);
        $display("RED_SPATIAL_STATS_TB_PASS");
        $finish;
    end
endmodule
