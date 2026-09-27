`timescale 1ns / 1ps

module red_pixel_mask_tb;
    reg  [15:0] pixel_rgb565;
    wire        is_red;
    integer failures;

    red_pixel_mask dut (
        .pixel_rgb565(pixel_rgb565),
        .is_red(is_red)
    );

    task check;
        input [15:0] pixel;
        input expected;
        begin
            pixel_rgb565 = pixel;
            #1;
            if (is_red !== expected) begin
                $display("FAIL pixel=%h expected=%b actual=%b", pixel, expected, is_red);
                failures = failures + 1;
            end
        end
    endtask

    initial begin
        failures = 0;
        check(16'h0000, 1'b0);                 // black
        check(16'hf800, 1'b1);                 // pure red
        check(16'h07e0, 1'b0);                 // green
        check(16'h001f, 1'b0);                 // blue
        check(16'hffff, 1'b0);                 // white
        check(16'hfc00, 1'b0);                 // orange-like background
        check({5'd28, 6'd26, 5'd17}, 1'b1);   // screen-derived red square
        check({5'd22, 6'd25, 5'd14}, 1'b1);   // retained raw-frame square median
        check({5'd15, 6'd17, 5'd6}, 1'b1);    // inclusive red and ratio limits
        check({5'd14, 6'd10, 5'd6}, 1'b0);   // red below limit
        check({5'd15, 6'd18, 5'd6}, 1'b0);   // red/green ratio below limit
        check({5'd22, 6'd30, 5'd22}, 1'b1);  // inclusive green limit
        check({5'd22, 6'd31, 5'd22}, 1'b0);  // green above limit
        check({5'd22, 6'd30, 5'd23}, 1'b0);  // blue above limit
        check({5'd20, 6'd20, 5'd5}, 1'b0);   // low-blue orange guard
        check({5'd20, 6'd12, 5'd0}, 1'b1);   // saturated red branch

        if (failures == 0)
            $display("RED_PIXEL_MASK_TB_PASS");
        else
            $fatal(1, "RED_PIXEL_MASK_TB_FAIL count=%0d", failures);
        $finish;
    end
endmodule
