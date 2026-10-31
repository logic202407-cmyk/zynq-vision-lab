`timescale 1ns/1ps
module uart_rx_tb;
    localparam integer HZ=100000000, DIV=868, BIT=8680;
    reg clk=0, reset_n=0, rx=1;
    always #5 clk=~clk;
    wire [7:0] data;
    wire valid, error, busy;
    uart_rx #(.CLOCK_HZ(HZ)) dut(clk,reset_n,rx,data,valid,error,busy);
    wire [7:0] bad_data;
    wire bad_valid,bad_error,bad_busy;
    uart_rx #(.BAUD(0)) invalid_config(clk,reset_n,rx,bad_data,bad_valid,bad_error,bad_busy);
    integer checks=0, count=0, errors=0, i, old_count;
    reg [7:0] received [0:1023];
    reg old_valid=0,old_error=0;
    task check;
        input condition;
        begin
            if (condition!==1'b1) $fatal(1,"RX check %0d time %0t",checks,$time);
            checks=checks+1;
        end
    endtask
    always @(negedge clk) begin
        if(reset_n) begin
            if(valid) begin received[count]=data; count=count+1; end
            if(error) errors=errors+1;
            if(valid && old_valid || error && old_error) $fatal(1,"RX pulse too long");
            if(valid && error) $fatal(1,"RX valid and error simultaneously");
            old_valid=valid; old_error=error;
        end else begin old_valid=0; old_error=0; end
    end
    task send_byte;
        input [7:0] value;
        input integer period;
        input bad_stop;
        integer k;
        begin
            rx=0; #(period);
            for(k=0;k<8;k=k+1) begin rx=value[k]; #(period); end
            rx=!bad_stop; #(period);
        end
    endtask
    initial begin
        #23; reset_n=1; #(BIT*2);
        check(count==0 && errors==0 && !busy);
        // False start shorter than half bit must not produce a byte.
        rx=0; #(BIT/4); rx=1; #(BIT*11);
        check(count==0 && errors==0);
        for(i=0;i<256;i=i+1) begin
            send_byte(i,BIT,0);
            check(count==i+1 && received[i]===i[7:0]);
        end
        // Independent asynchronous baud error in both directions, all patterns.
        for(i=0;i<256;i=i+1) begin
            send_byte(i,8506,0);
            check(count==257+i && received[256+i]===i[7:0]);
        end
        for(i=0;i<256;i=i+1) begin
            send_byte(i,8854,0);
            check(count==513+i && received[512+i]===i[7:0]);
        end
        old_count=count;
        send_byte(8'h55,BIT,1); #(BIT*20);
        check(count==old_count && errors==1); // held-low break reports once
        rx=1; #(BIT*2); send_byte(8'ha5,BIT,0);
        check(count==old_count+1 && received[old_count]==8'ha5);
        rx=0; #(BIT*3); reset_n=0; #47; rx=1; reset_n=1; #(BIT*12);
        check(count==old_count+1 && !busy);
        send_byte(8'h3c,BIT,0);
        check(received[count-1]==8'h3c && !bad_valid && !bad_error && !bad_busy);
        $display("UART_RX_TB_PASS checks=%0d bytes=%0d errors=%0d",checks,count,errors);
        $finish;
    end
    initial begin #100000000; $fatal(1,"RX watchdog"); end
endmodule
