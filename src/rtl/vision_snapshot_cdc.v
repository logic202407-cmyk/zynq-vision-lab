`timescale 1ns/1ps
// Single-entry bundled-data mailbox. Either domain reset flushes BOTH ends.
// Payload held until destination consumption; busy arrivals are counted/dropped.
module vision_snapshot_cdc #(parameter WIDTH=1)(
 input wire src_clk,dst_clk,src_reset_n,dst_reset_n,
 input wire src_valid,input wire[WIDTH-1:0] src_data,
 output wire src_ready,output reg[31:0] dropped,
 output reg dst_valid,output reg[WIDTH-1:0] dst_data,input wire dst_ready
);
 wire arst_n=src_reset_n&&dst_reset_n;
 (* ASYNC_REG="TRUE", SHREG_EXTRACT="NO" *) reg[1:0] sr,dr,req_sync,ack_sync;
 reg request,ack;reg[WIDTH-1:0] holding;
 always @(posedge src_clk or negedge arst_n)if(!arst_n)sr<=0;else sr<={sr[0],1'b1};
 always @(posedge dst_clk or negedge arst_n)if(!arst_n)dr<=0;else dr<={dr[0],1'b1};
 always @(posedge src_clk or negedge arst_n)if(!arst_n)ack_sync<=0;else ack_sync<={ack_sync[0],ack};
 always @(posedge dst_clk or negedge arst_n)if(!arst_n)req_sync<=0;else req_sync<={req_sync[0],request};
 assign src_ready=sr[1]&&(request==ack_sync[1]);
 always @(posedge src_clk or negedge arst_n)begin
  if(!arst_n)begin request<=0;holding<=0;dropped<=0;end
  else if(!sr[1])begin request<=0;dropped<=0;end
  else begin
   if(src_valid)if(src_ready)begin holding<=src_data;request<=!request;end else dropped<=dropped+1;
  end
 end
 always @(posedge dst_clk or negedge arst_n)begin
  if(!arst_n)begin ack<=0;dst_valid<=0;dst_data<=0;end
  else if(!dr[1])begin ack<=0;dst_valid<=0;end
  else begin
   if(!dst_valid&&req_sync[1]!=ack)begin dst_data<=holding;dst_valid<=1;end
   if(dst_valid&&dst_ready)begin dst_valid<=0;ack<=req_sync[1];end
  end
 end
endmodule
