`timescale 1ns/1ps
// Single-entry bundled-data mailbox. Either domain reset flushes BOTH ends.
// Payload held until destination consumption; busy arrivals are counted/dropped.
module vision_snapshot_cdc #(parameter WIDTH=1,LOCAL_RESETS=0)(
 input wire src_clk,dst_clk,src_reset_n,dst_reset_n,
 input wire src_valid,input wire[WIDTH-1:0] src_data,
 output wire src_ready,output reg[31:0] dropped,
 output reg dst_valid,output reg[WIDTH-1:0] dst_data,input wire dst_ready
);
 wire arst_n=src_reset_n&&dst_reset_n;
 (* ASYNC_REG="TRUE", SHREG_EXTRACT="NO" *) reg[1:0] req_sync,ack_sync;
 reg request,ack;reg[WIDTH-1:0] holding;
 // Only the release chains see the asynchronous cross-domain reset request.
 // Functional state and toggle synchronizers use their OWN clock's release.
 // Either reset still asserts both releases asynchronously, including short pulses.
 // LOCAL_RESETS requires a common assertion source and ONE upstream release
 // chain per clock. No independent reset request may bypass that common source.
 // Reuse those chains rather than reconverging duplicated reset synchronizers.
 wire src_run_n,dst_run_n;
 generate if(LOCAL_RESETS)begin:local_release
  assign src_run_n=src_reset_n;assign dst_run_n=dst_reset_n;
 end else begin:internal_release
  (* ASYNC_REG="TRUE", SHREG_EXTRACT="NO" *) reg[1:0] sr,dr;
  always @(posedge src_clk or negedge arst_n)if(!arst_n)sr<=0;else sr<={sr[0],1'b1};
  always @(posedge dst_clk or negedge arst_n)if(!arst_n)dr<=0;else dr<={dr[0],1'b1};
  assign src_run_n=sr[1];assign dst_run_n=dr[1];
 end endgenerate
 always @(posedge src_clk or negedge src_run_n)if(!src_run_n)ack_sync<=0;else ack_sync<={ack_sync[0],ack};
 always @(posedge dst_clk or negedge dst_run_n)if(!dst_run_n)req_sync<=0;else req_sync<={req_sync[0],request};
 assign src_ready=src_run_n&&(request==ack_sync[1]);
 always @(posedge src_clk or negedge src_run_n)begin
  if(!src_run_n)begin request<=0;holding<=0;dropped<=0;end
  else begin
   if(src_valid)if(src_ready)begin holding<=src_data;request<=!request;end else dropped<=dropped+1;
  end
 end
 always @(posedge dst_clk or negedge dst_run_n)begin
  if(!dst_run_n)begin ack<=0;dst_valid<=0;dst_data<=0;end
  else begin
   if(!dst_valid&&req_sync[1]!=ack)begin dst_data<=holding;dst_valid<=1;end
   if(dst_valid&&dst_ready)begin dst_valid<=0;ack<=req_sync[1];end
  end
 end
endmodule
