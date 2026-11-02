`timescale 1ns/1ps
// Offline candidate only. The external provider must durably reserve a fresh
// interval for EACH reset. This volatile guard cannot detect rollback/replay
// of a whole grant across reset and is NOT connected to the board wrapper.
module epoch_qid_allocator(
 input wire clk, reset_n, load,
 input wire [127:0] range_start, range_end,
 input wire take, stop_take,
 output reg [127:0] qid,
 output reg qid_valid, denied, active, fault,
 output wire stop_only
);
 reg old_load;
 reg [127:0] next_qid, limit, last_end;
 assign stop_only=active && next_qid==limit;
 always @(posedge clk or negedge reset_n) begin
  if(!reset_n) begin
   old_load<=0;next_qid<=0;limit<=0;last_end<=0;qid<=0;
   qid_valid<=0;denied<=0;active<=0;fault<=0;
  end else begin
   old_load<=load;qid_valid<=0;denied<=0;
   if(!fault) begin
    if(load&&!old_load) begin
     if(active || take || stop_take || range_start==0 ||
        range_end<range_start || range_start<=last_end) begin
      fault<=1;active<=0;denied<=1;
     end else begin
      next_qid<=range_start;limit<=range_end;last_end<=range_end;active<=1;
     end
    end else if(take&&stop_take) begin
     fault<=1;active<=0;denied<=1;
    end else if(take||stop_take) begin
     if(!active) denied<=1;
     else if(take&&stop_only) denied<=1; // Preserve final ID for STOP.
     else begin
      qid<=next_qid;qid_valid<=1;
      if(stop_take) active<=0; // Burn all remaining IDs after stopping.
      else next_qid<=next_qid+1'b1; // Strictly below limit; cannot wrap.
     end
    end
   end else if(load||take||stop_take) denied<=1;
  end
 end
endmodule
