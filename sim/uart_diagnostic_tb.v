`timescale 1ns/1ps
module uart_diagnostic_tb;
    // 100 MHz simulation clock; rounded divider=868 clocks, 8680ns/bit.
    localparam integer CLOCK_HZ=100000000, BAUD=115200, DIV=(CLOCK_HZ+BAUD/2)/BAUD;
    localparam integer BIT_NS=DIV*10;
    reg clk=0;
    always #5 clk=~clk;
    reg reset_n=0, stop=0, valid=0;
    reg [7:0] data=0;
    wire tx,ready,busy,done;
    uart_tx_8n1 #(.CLOCK_HZ(CLOCK_HZ),.BAUD(BAUD)) byte_dut
        (clk,reset_n,stop,valid,data,ready,tx,busy,done);
    wire invalid_ready, invalid_tx, invalid_busy, invalid_done;
    uart_tx_8n1 #(.CLOCK_HZ(1),.BAUD(0)) invalid_dut
        (clk,reset_n,stop,valid,data,invalid_ready,invalid_tx,invalid_busy,invalid_done);
    reg diag_reset=0, request_local=0, trigger=0, query=1, diag_stop=0;
    reg pc_line=1, device_line=1;
    wire diag_tx,pc_rx,owner,diag_busy,diag_done,aborted,rejected;
    zynq_uart_diagnostic #(.CLOCK_HZ(CLOCK_HZ),.BAUD(BAUD)) diag_dut
        (clk,diag_reset,request_local,trigger,query,diag_stop,pc_line,device_line,
         diag_tx,pc_rx,owner,diag_busy,diag_done,aborted,rejected);
    integer checks=0, completions=0, diag_completions=0, rejects=0;
    integer i,j;
    reg [7:0] value;
    reg previous_done=0;
    task check;
        input condition;
        begin if (!condition) $fatal(1,"Check %0d failed at %0t",checks,$time); checks=checks+1; end
    endtask
    always @(negedge clk) begin
        if(reset_n) begin
            if(done) completions=completions+1;
            if(done && previous_done) $fatal(1,"done lasted longer than one cycle");
            previous_done=done;
        end else previous_done=0;
        if(diag_reset) begin
            if(diag_done) diag_completions=diag_completions+1;
            if(rejected) rejects=rejects+1;
        end
    end
    task send;
        input [7:0] b;
        begin
            wait(ready); @(negedge clk); data=b; valid=1;
            @(negedge clk); valid=0;
        end
    endtask
    task receive_byte;
        input diagnostic;
        input [7:0] expected;
        reg [7:0] received;
        integer k;
        begin
            if(diagnostic) @(negedge diag_tx); else @(negedge tx);
            #(BIT_NS/2);
            check(diagnostic ? diag_tx===0 : tx===0);
            for(k=0;k<8;k=k+1) begin
                #(BIT_NS);
                received[k]=diagnostic ? diag_tx : tx;
            end
            #(BIT_NS);
            check(diagnostic ? diag_tx===1 : tx===1);
            check(received===expected);
        end
    endtask
    task fire;
        begin
            trigger=0;
            @(negedge clk); @(negedge clk); trigger=1;
            @(negedge clk); trigger=0;
        end
    endtask
    initial begin
        #1; check(tx===1 && diag_tx===1 && !busy && !diag_busy);
        #34; reset_n=1;diag_reset=1;
        repeat(10) @(negedge clk); check(completions==0 && diag_completions==0 && !owner);
        // All 256 normal byte patterns and stop-bit/busy completion.
        for(i=0;i<256;i=i+1) begin
            fork send(i); receive_byte(0,i); join
            check(busy); wait(done); #1; check(tx===1 && ready && !busy);
        end
        repeat(2) @(negedge clk); check(completions==256);
        check(invalid_tx===1 && !invalid_ready && !invalid_busy && !invalid_done);
        // valid while busy must not overwrite the accepted byte.
        fork
            begin send(8'ha5); #(2*BIT_NS); @(negedge clk);data=0;valid=1;
                @(negedge clk);valid=0;end
            receive_byte(0,8'ha5);
        join
        wait(done); repeat(2) @(negedge clk); check(completions==257 && !busy);
        // Back-to-back valid stream handshakes, no externally inserted byte gap.
        fork
            begin for(j=0;j<4;j=j+1) send(8'h30+j);end
            begin receive_byte(0,8'h30);receive_byte(0,8'h31);
                receive_byte(0,8'h32);receive_byte(0,8'h33);end
        join
        wait(done);repeat(2) @(negedge clk);check(completions==261);
        stop=1;valid=1;data=8'h00;#(2*BIT_NS);check(tx===1 && !ready && !busy);
        valid=0;stop=0;
        // Mid-byte stop finishes the accepted byte, no next byte allowed.
        fork
            begin send(8'h00);#(2*BIT_NS);stop=1;end
            receive_byte(0,8'h00);
        join
        wait(done);repeat(2) @(negedge clk);check(!ready && tx===1 && !busy);
        stop=0;
        $display("UART_BYTE_TESTS_PASS checks=%0d",checks);
        send(8'h00);#(2*BIT_NS);reset_n=0;#1;check(tx===1 && !busy && !done);
        #100;reset_n=1;repeat(5) @(negedge clk);check(tx===1 && ready && !done);

        // No startup diagnostic transmission; held-high trigger across reset is suppressed.
        trigger=1;diag_reset=0;#20;diag_reset=1;
        #(13*BIT_NS);check(!diag_busy && diag_completions==0);
        trigger=0;
        repeat(2) @(negedge clk);
        fire();repeat(3) @(negedge clk);check(rejects>0 && !diag_busy && !owner);
        // Ownership cannot switch with an active PC line, even if requested.
        pc_line=0;request_local=1;#(13*BIT_NS);check(!owner && diag_tx===0);
        pc_line=1;#(13*BIT_NS);check(owner && diag_tx===1);
        device_line=0;#2;check(pc_rx===0);device_line=1;
        // Manual query only: st LF; repeated trigger while busy is rejected.
        fork
            begin fire();#(2*BIT_NS);fire();end
            begin receive_byte(1,"s");receive_byte(1,"t");receive_byte(1,8'h0a);end
        join
        wait(diag_done);repeat(3) @(negedge clk);check(!aborted && !diag_busy && diag_completions==1);
        check(rejects>=2);
        // Bounded diagnostic sends exactly __diag__ LF, never a motion command.
        query=0;
        fork
            fire();
            begin receive_byte(1,"_");receive_byte(1,"_");receive_byte(1,"d");
                receive_byte(1,"i");receive_byte(1,"a");receive_byte(1,"g");
                receive_byte(1,"_");receive_byte(1,"_");receive_byte(1,8'h0a);end
        join
        wait(diag_done);repeat(3) @(negedge clk);check(!aborted && diag_completions==2);
        // Stop during first byte, finish it, terminate message, report abort.
        query=1;
        fork
            begin fire();#(2*BIT_NS);diag_stop=1;end
            receive_byte(1,"s");
        join
        wait(diag_done);repeat(3) @(negedge clk);check(aborted && !diag_busy && diag_tx===1);
        #(15*BIT_NS);check(diag_completions==3 && !diag_busy);
        fire();repeat(3) @(negedge clk);check(!diag_busy);
        diag_stop=0;
        // Stopping before any byte is accepted produces no spurious start bit.
        fire();diag_stop=1;wait(diag_done);#1;check(diag_tx===1 && aborted);
        diag_stop=0;
        // Held trigger causes one transaction only, not a repeated stream.
        fork
            begin @(negedge clk);trigger=1;end
            begin receive_byte(1,"s");receive_byte(1,"t");receive_byte(1,8'h0a);end
        join
        wait(diag_done);#(35*BIT_NS);check(!diag_busy && diag_tx===1);trigger=0;
        // Releasing ownership waits until local transaction is complete/idle.
        fork
            begin fire();#(2*BIT_NS);request_local=0;check(owner);end
            begin receive_byte(1,"s");receive_byte(1,"t");receive_byte(1,8'h0a);end
        join
        wait(diag_done);#(13*BIT_NS);check(!owner);
        pc_line=0;#1;check(diag_tx===0);pc_line=1;
        // Reset during a diagnostic abandons bytes, restores high and PC ownership.
        request_local=1;#(13*BIT_NS);check(owner);fire();#(2*BIT_NS);
        diag_reset=0;#1;check(diag_tx===1 && !diag_busy && !owner && !diag_done);
        diag_reset=1;request_local=0;#(15*BIT_NS);check(!diag_busy && diag_tx===1);
        $display("UART_DIAGNOSTIC_TB_PASS checks=%0d divisor=%0d baud=%0d",checks,DIV,CLOCK_HZ/DIV);
        $finish;
    end
    initial begin #100000000; $fatal(1,"UART test timeout"); end
endmodule
