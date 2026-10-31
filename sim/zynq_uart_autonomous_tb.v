`timescale 1ns/1ps
module zynq_uart_autonomous_tb;
    localparam BIT=8680, DB=8, LIMIT=200000;
    reg clk=0,reset_n=0,start=1,command_stop=0,request_local=0,ack=0;
    reg pc_rx=1,skystar_rx=1;
    always #5 clk=~clk;
    wire pc_tx,skystar_tx,owner,busy,tx_busy,tx_done,done,timeout,error,rejected;
    wire [7:0] rx_data;
    wire rx_valid,rx_error;
    wire [1:0] phase;
    zynq_uart_autonomous #(.CLOCK_HZ(100000000),.DEBOUNCE_CYCLES(DB),
        .RESPONSE_CYCLES(LIMIT)) dut(clk,reset_n,start,command_stop,request_local,
        ack,pc_rx,skystar_rx,pc_tx,skystar_tx,owner,busy,tx_busy,tx_done,done,
        timeout,error,rejected,rx_data,rx_valid,rx_error,phase);
    integer checks=0,tx_count=0,rx_count=0,done_count=0,rejects=0,tx_ends=0;
    integer before_tx,before_done,before_rx,i,wait_cycles;
    reg [7:0] sent [0:127];
    reg [7:0] received [0:127];
    reg [7:0] decoded;
    integer bit_index;
    reg monitor=1;
    task check;
        input condition;
        begin
            if(condition!==1'b1) $fatal(1,"AUTO check %0d time %0t tx=%0d phase=%0d",checks,$time,tx_count,phase);
            checks=checks+1;
        end
    endtask
    always @(negedge clk) if(reset_n) begin
        if(rx_valid) begin received[rx_count]=rx_data; rx_count=rx_count+1; end
        if(done) done_count=done_count+1;
        if(tx_done) tx_ends=tx_ends+1;
        if(rejected) rejects=rejects+1;
        if(pc_tx!==skystar_rx) $fatal(1,"return transparency");
    end
    // Independent wire decoder, not DUT TX state or RX loopback.
    initial forever begin
        @(negedge skystar_tx);
        if(owner && monitor) begin
            #(BIT/2); check(skystar_tx===0);
            for(bit_index=0;bit_index<8;bit_index=bit_index+1) begin
                #(BIT); decoded[bit_index]=skystar_tx;
            end
            #(BIT); check(skystar_tx===1);
            sent[tx_count]=decoded; tx_count=tx_count+1;
        end
    end
    task fire;
        input stop_command;
        begin
            @(negedge clk); start=0; command_stop=stop_command;
            repeat(DB+5) @(negedge clk);
            start=1; repeat(DB+5) @(negedge clk);
            start=0;
        end
    endtask
    task reply_byte;
        input [7:0] value;
        input bad_stop;
        integer k;
        begin
            skystar_rx=0; #(BIT);
            for(k=0;k<8;k=k+1) begin skystar_rx=value[k]; #(BIT); end
            skystar_rx=!bad_stop; #(BIT);
        end
    endtask
    task expect_query;
        input integer offset;
        begin
            check(tx_count==offset+4);
            check(sent[offset]=="s" && sent[offset+1]=="t" &&
                sent[offset+2]==13 && sent[offset+3]==10);
        end
    endtask
    initial begin
        #23; reset_n=1; #(BIT*15);
        check(tx_count==0 && !busy && !owner && skystar_tx===1);
        request_local=1; start=0; #(BIT*15);
        check(!owner); // no pause acknowledgment, no switch
        ack=1; #(BIT*15); check(owner);
        // Sub-debounce bounce does not send; a stable release rearms once.
        repeat(4) begin start=1; #20; start=0; #20; end
        #(BIT); check(tx_count==0 && !busy);
        fire(0); wait(tx_done); #20; expect_query(0);
        before_rx=rx_count;
        reply_byte("O",0); reply_byte("K",0); reply_byte(13,0); reply_byte(10,0);
        #30; check(!busy && !timeout && !error && done_count==1);
        check(rx_count==before_rx+4 && received[before_rx]=="O" &&
            received[before_rx+1]=="K" && received[before_rx+2]==13 && received[before_rx+3]==10);
        // Busy press is consumed, command selection changes cannot alter ROM.
        fire(1); command_stop=0; fire(0);
        wait(tx_done); #20;
        check(tx_count==10 && rejects==1);
        check(sent[4]=="s" && sent[5]=="t" && sent[6]=="o" &&
            sent[7]=="p" && sent[8]==13 && sent[9]==10);
        // Count from observed entry to WAIT_REPLY, including the two clocks
        // already consumed above. Timeout must not depend on reply activity.
        wait_cycles=2;
        while(busy) begin @(posedge clk); #1; wait_cycles=wait_cycles+1; end
        check(wait_cycles==LIMIT+1);
        #20; check(timeout && !busy && done_count==2);
        #(BIT*15); check(tx_count==10); // no retransmit on missing reply
        // Held press triggers one command even beyond timeout.
        start=1; wait(tx_done); #20; expect_query(10);
        wait(done); #(BIT*15); check(tx_count==14 && timeout);
        start=0; repeat(DB+5) @(negedge clk);
        fire(0); wait(tx_done); #20;
        reply_byte(8'h55,1); #(BIT); check(error && !busy && !timeout);
        skystar_rx=1; #(BIT*3);
        // Mid-command mode request must finish all bytes and wait/timeout.
        before_tx=tx_count;
        fire(1); request_local=0; wait(tx_done); #20;
        check(owner && tx_count==before_tx+6);
        wait(done); #(BIT*15); check(!owner);
        // Transparent PC frame: switching requested during 0xff high data must
        // not truncate the byte. Ack held low through complete PC frame.
        pc_rx=0; #100; check(skystar_tx===0);
        request_local=1; ack=0; #(BIT-100); pc_rx=1;
        #(BIT*8); check(!owner && skystar_tx===1);
        #(BIT); ack=1; #(BIT*15); check(owner);
        // A complete transaction after a framing fault is possible, no retry.
        before_tx=tx_count;
        fire(0); wait(tx_done); #20; expect_query(before_tx);
        reply_byte(10,0); #20; check(!busy && !timeout && !error);
        // Local ownership must isolate PC traffic; no raw PC bit leaks into
        // the independently decoded status command. Ack loss cannot steal TX.
        before_tx=tx_count;
        fork
            begin fire(0); wait(tx_done); end
            begin
                #(BIT); ack=0;
                repeat(30) begin pc_rx=0; #(BIT/3); pc_rx=1; #(BIT/3); end
            end
        join
        #20; expect_query(before_tx); check(owner);
        // Non-LF traffic does not postpone the absolute timeout indefinitely.
        fork
            begin repeat(25) reply_byte("x",0); end
            begin wait(done); #20; check(timeout && !busy); end
        join
        pc_rx=1; ack=1; #(BIT*15); check(tx_count==before_tx+4);
        // Reset while awaiting response: no retry and no stale completion.
        fire(0); wait(tx_done); #20;
        reset_n=0; start=1; #35; reset_n=1;
        #(BIT*15); check(!busy && !owner && !timeout && !error);
        start=0; #(BIT*15); check(owner);
        // Midbyte reset explicitly aborts a frame, forces idle and requires
        // new stable release/press. This is not a glitchless mode handoff.
        monitor=0; fire(0); #(BIT*2); reset_n=0; start=1; #1;
        check(skystar_tx===1 && !busy && !tx_busy);
        #35; reset_n=1; #(BIT*20);
        check(!busy && !owner && skystar_tx===1);
        start=0; #(BIT*15); monitor=1; check(owner);
        before_tx=tx_count; fire(0); wait(tx_done); #20; expect_query(before_tx);
        reply_byte(10,0); #20; check(!busy && !timeout);
        $display("ZYNQ_UART_AUTONOMOUS_TB_PASS checks=%0d sent_bytes=%0d received_bytes=%0d completed=%0d rejected=%0d",checks,tx_count,rx_count,done_count,rejects);
        $finish;
    end
    initial begin #50000000; $fatal(1,"AUTO watchdog"); end
endmodule
