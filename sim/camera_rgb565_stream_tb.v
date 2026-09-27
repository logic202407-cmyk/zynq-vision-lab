`timescale 1ns / 1ps

module camera_rgb565_stream_tb;
    reg cam_pclk = 1'b0;
    always #5 cam_pclk = ~cam_pclk;
    reg rst_n = 1'b0;
    reg cam_vsync = 1'b0;
    reg cam_href = 1'b0;
    reg [7:0] cam_data = 8'd0;
    wire pixel_valid;
    wire frame_start;
    wire frame_end;
    wire [15:0] pixel_rgb565;
    wire [9:0] pixel_x;
    wire [8:0] pixel_y;
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
    integer seen_pixels = 0;
    reg result_seen = 1'b0;
    reg observed_complete = 1'b0;
    reg observed_target = 1'b0;
    reg [18:0] observed_count = 19'd0;
    reg [27:0] observed_sum_x = 28'd0;
    reg [27:0] observed_sum_y = 28'd0;
    reg [9:0] observed_min_x = 10'd0;
    reg [8:0] observed_min_y = 9'd0;
    reg [9:0] observed_max_x = 10'd0;
    reg [8:0] observed_max_y = 9'd0;
    integer x;
    integer y;

    camera_rgb565_stream #(.WIDTH(4), .HEIGHT(3)) adapter (
        .cam_pclk(cam_pclk), .rst_n(rst_n), .cam_vsync(cam_vsync),
        .cam_href(cam_href), .cam_data(cam_data),
        .pixel_valid(pixel_valid), .frame_start(frame_start),
        .frame_end(frame_end), .pixel_rgb565(pixel_rgb565),
        .pixel_x(pixel_x), .pixel_y(pixel_y)
    );
    red_frame_stats #(.WIDTH(4), .HEIGHT(3)) stats (
        .clk(cam_pclk), .rst_n(rst_n), .pixel_valid(pixel_valid),
        .frame_start(frame_start), .frame_end(frame_end),
        .pixel_rgb565(pixel_rgb565), .pixel_x(pixel_x), .pixel_y(pixel_y),
        .result_strobe(result_strobe), .frame_complete(frame_complete),
        .target_valid(target_valid), .red_count(red_count),
        .red_sum_x(red_sum_x), .red_sum_y(red_sum_y),
        .red_min_x(red_min_x), .red_min_y(red_min_y),
        .red_max_x(red_max_x), .red_max_y(red_max_y)
    );

    always @(posedge cam_pclk) begin
        #2;
        if (result_strobe) begin
            result_seen = 1'b1;
            observed_complete = frame_complete;
            observed_target = target_valid;
            observed_count = red_count;
            observed_sum_x = red_sum_x;
            observed_sum_y = red_sum_y;
            observed_min_x = red_min_x;
            observed_min_y = red_min_y;
            observed_max_x = red_max_x;
            observed_max_y = red_max_y;
        end
        if (pixel_valid) begin
            if (pixel_x !== (seen_pixels % 4) || pixel_y !== (seen_pixels / 4) ||
                pixel_rgb565 !== (((seen_pixels == 0) || (seen_pixels == 11)) ? 16'hf800 : 16'h0000) ||
                frame_start !== (seen_pixels == 0) || frame_end !== (seen_pixels == 11)) begin
                $display("FAIL adapter pixel=%0d x=%0d y=%0d value=%h sof=%b eof=%b",
                         seen_pixels, pixel_x, pixel_y, pixel_rgb565,
                         frame_start, frame_end);
                failures = failures + 1;
            end
            seen_pixels = seen_pixels + 1;
        end
    end

    task send_byte;
        input [7:0] value;
        begin
            @(negedge cam_pclk);
            cam_href = 1'b1;
            cam_data = value;
        end
    endtask

    task send_pixel;
        input [15:0] value;
        begin
            send_byte(value[15:8]);
            send_byte(value[7:0]);
        end
    endtask

    initial begin
        repeat (2) @(negedge cam_pclk);
        rst_n = 1'b1;
        cam_vsync = 1'b1;
        repeat (2) @(negedge cam_pclk);
        cam_vsync = 1'b0;
        for (y = 0; y < 3; y = y + 1) begin
            for (x = 0; x < 4; x = x + 1)
                send_pixel(((x == 0 && y == 0) || (x == 3 && y == 2)) ?
                           16'hf800 : 16'h0000);
            @(negedge cam_pclk);
            cam_href = 1'b0;
            cam_data = 8'd0;
            repeat (3) @(negedge cam_pclk);
        end
        if (seen_pixels != 12 || result_seen !== 1'b1 ||
            observed_complete !== 1'b1 || observed_target !== 1'b1 ||
            observed_count !== 19'd2 || observed_sum_x !== 28'd3 ||
            observed_sum_y !== 28'd2 || observed_min_x !== 10'd0 ||
            observed_min_y !== 9'd0 || observed_max_x !== 10'd3 ||
            observed_max_y !== 9'd2) begin
            $display("FAIL frame seen=%0d strobe=%b complete=%b count=%0d sum=(%0d,%0d)",
                     seen_pixels, result_strobe, frame_complete, red_count,
                     red_sum_x, red_sum_y);
            failures = failures + 1;
        end
        if (failures == 0)
            $display("CAMERA_RGB565_STREAM_TB_PASS");
        else
            $fatal(1, "CAMERA_RGB565_STREAM_TB_FAIL count=%0d", failures);
        $finish;
    end
endmodule
