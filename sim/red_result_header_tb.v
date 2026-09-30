`timescale 1ns / 1ps

module red_result_header_tb;
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0;
    reg result_strobe = 0;
    reg frame_complete = 0;
    reg target_valid = 0;
    reg [18:0] red_count = 0;
    reg [27:0] red_sum_x = 0, red_sum_y = 0;
    reg [9:0] red_min_x = 0, red_max_x = 0;
    reg [8:0] red_min_y = 0, red_max_y = 0;
    reg [5:0] header_index = 0;
    wire [7:0] header_byte;
    wire [7:0] filtered_header_byte;
    reg [255:0] observed;
    reg [255:0] observed_filtered;
    integer i;

    red_result_header dut (
        .clk(clk), .rst_n(rst_n), .result_strobe(result_strobe),
        .frame_complete(frame_complete), .target_valid(target_valid),
        .red_count(red_count), .red_sum_x(red_sum_x), .red_sum_y(red_sum_y),
        .red_min_x(red_min_x), .red_min_y(red_min_y),
        .red_max_x(red_max_x), .red_max_y(red_max_y),
        .header_index(header_index), .header_byte(header_byte)
    );

    red_result_header #(.MASK_VERSION(8'd2)) filtered_dut (
        .clk(clk), .rst_n(rst_n), .result_strobe(result_strobe),
        .frame_complete(frame_complete), .target_valid(target_valid),
        .red_count(red_count), .red_sum_x(red_sum_x), .red_sum_y(red_sum_y),
        .red_min_x(red_min_x), .red_min_y(red_min_y),
        .red_max_x(red_max_x), .red_max_y(red_max_y),
        .header_index(header_index), .header_byte(filtered_header_byte)
    );

    task read_extension;
        begin
            observed = 256'd0;
            observed_filtered = 256'd0;
            for (i = 8; i < 40; i = i + 1) begin
                header_index = i;
                #1;
                observed = {observed[247:0], header_byte};
                observed_filtered = {observed_filtered[247:0], filtered_header_byte};
            end
            if (observed_filtered !== {observed[255:184], 8'd2, observed[175:0]})
                $fatal(1, "Filtered extension version mismatch");
        end
    endtask

    initial begin
        repeat (2) @(negedge clk);
        rst_n = 1;
        read_extension();
        if (observed !== {32'd1, 32'd0, 8'd0, 8'd1, 16'd0,
                          32'd0, 32'd0, 32'd0, 16'd0, 16'd0, 16'd0, 16'd0})
            $fatal(1, "Initial extension mismatch: %h", observed);
        @(negedge clk);
        result_strobe = 1;
        frame_complete = 1;
        target_valid = 1;
        red_count = 19'h12345;
        red_sum_x = 28'h456789a;
        red_sum_y = 28'h56789ab;
        red_min_x = 10'h123;
        red_min_y = 9'h101;
        red_max_x = 10'h234;
        red_max_y = 9'h178;
        @(negedge clk);
        result_strobe = 0;
        read_extension();
        if (observed !== {32'd2, 32'd1, 8'd3, 8'd1, 16'd0,
                          32'h00012345, 32'h0456789a, 32'h056789ab,
                          16'h0123, 16'h0101, 16'h0234, 16'h0178})
            $fatal(1, "Populated extension mismatch: %h", observed);
        $display("RED_RESULT_HEADER_TB_PASS");
        $finish;
    end
endmodule
