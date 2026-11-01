`timescale 1ns/1ps
// Same camera clock as red_frame_stats. Counts ALL completed results, transmits
// every Nth result. Tick is a camera-clock counter, NOT wall time/milliseconds.
module camera_measurement_snapshot #(
 parameter integer EVERY_N=3
)(input wire clk,reset_n,result_strobe,complete,target,
 input wire[18:0] count,input wire[27:0] sum_x,sum_y,
 input wire[9:0] xmin,xmax,input wire[8:0] ymin,ymax,
 output reg strobe,output reg[218:0] snapshot,
 output reg[31:0] frame_seq,capture_tick);
 reg[31:0] divider;
 always @(posedge clk or negedge reset_n)begin
  if(!reset_n)begin strobe<=0;snapshot<=0;frame_seq<=0;capture_tick<=0;divider<=0;end
  else begin
   strobe<=0;capture_tick<=capture_tick+1;
   if(result_strobe)begin
    frame_seq<=frame_seq+1;
    if(divider==EVERY_N-1)begin
     divider<=0;strobe<=1;
     snapshot<={8'd2,16'd640,16'd480,frame_seq+32'd1,capture_tick,
       complete,target,count,sum_x,sum_y,xmin,ymin,xmax,ymax};
    end else divider<=divider+1;
   end
  end
 end
endmodule
