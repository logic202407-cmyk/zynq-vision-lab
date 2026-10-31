`timescale 1ns/1ps
module zynq_uart_bridge_tb;
    reg pc_rx = 1, skystar_rx = 1;
    wire pc_tx, skystar_tx;
    zynq_uart_bridge dut(pc_rx, pc_tx, skystar_rx, skystar_tx);
    // Approximate 115200 baud, concurrent independent full-duplex streams.
    task pc_byte(input [7:0] value);
        integer i;
        begin
            pc_rx=0; #8681;
            for(i=0;i<8;i=i+1) begin pc_rx=value[i]; #8681; end
            pc_rx=1; #8681;
        end
    endtask
    task device_byte(input [7:0] value);
        integer i;
        begin
            skystar_rx=0; #8681;
            for(i=0;i<8;i=i+1) begin skystar_rx=value[i]; #8681; end
            skystar_rx=1; #8681;
        end
    endtask
    always @(pc_rx or skystar_rx) begin
        #1;
        if (skystar_tx !== pc_rx || pc_tx !== skystar_rx)
            $fatal(1,"Full duplex routing mismatch");
    end
    integer n;
    initial begin
        #10;
        if (pc_tx !== 1 || skystar_tx !== 1) $fatal(1,"Idle mismatch");
        fork
            begin for(n=0;n<256;n=n+1) pc_byte(n); end
            begin
                repeat(64) begin
                    device_byte(8'h00); device_byte(8'hff);
                    device_byte(8'haa); device_byte(8'h55);
                end
            end
        join
        #10;
        $display("ZYNQ_UART_BRIDGE_TB_PASS");
        $finish;
    end
endmodule
