`timescale 1ns/1ps
// Candidate reconstruction of the documented transparent bridge.
// No packet buffering or autonomous commands; pin directions must be reviewed
// against the actual board before implementation. This is not the old bitstream.
module zynq_uart_bridge (
    input wire pc_rx,
    output wire pc_tx,
    input wire skystar_rx,
    output wire skystar_tx
);
    assign skystar_tx = pc_rx;
    assign pc_tx = skystar_rx;
endmodule
