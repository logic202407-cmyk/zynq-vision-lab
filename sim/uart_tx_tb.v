`timescale 1ns/1ps
module uart_tx_tb;
    reg clk=0,reset_n=0,valid=0,stop=0;
    reg [7:0] data=0;
    always #5 clk=~clk;
    wire ready,tx,busy,done;
    uart_tx_8n1 #(.CLOCK_HZ(100000000)) dut(clk,reset_n,stop,valid,data,ready,tx,busy,done);
    integer checks=0,i,j,k,completed=0;
    reg [9:0] expected;
    task check;
        input condition;
        begin
            if(condition!==1'b1) $fatal(1,"TX check %0d at %0t",checks,$time);
            checks=checks+1;
        end
    endtask
    always @(negedge clk) if(done) completed=completed+1;
    initial begin
        #1; check(tx===1 && !busy);
        #24; reset_n=1;
        for(i=0;i<256;i=i+1) begin
            @(negedge clk); data=i; valid=1; expected={1'b1,i[7:0],1'b0};
            @(posedge clk); #1;
            for(j=0;j<10;j=j+1) begin
                // Assert every clock, not only bit centers. Busy requests use
                // deliberately different data and must not overwrite the frame.
                for(k=0;k<868;k=k+1) begin
                    check(tx===expected[j] && busy && !done && !ready);
                    @(negedge clk); data=~i; valid=(j==3); stop=(j==6);
                    @(posedge clk); #1;
                end
            end
            check(done && !busy && tx===1);
            @(negedge clk); valid=0; stop=0;
        end
        check(completed==256);
        @(negedge clk); valid=1; data=0;
        repeat(100) @(negedge clk);
        reset_n=0; #1; check(tx===1 && !busy && !done);
        valid=0; #24; reset_n=1;
        repeat(9000) @(negedge clk);
        check(tx===1 && !busy && completed==256);
        stop=1; valid=1; repeat(20) @(negedge clk);
        check(!ready && !busy && tx===1);
        $display("UART_TX_TB_PASS checks=%0d bytes=%0d",checks,completed);
        $finish;
    end
    initial begin #100000000; $fatal(1,"TX watchdog"); end
endmodule
