`timescale 1ns/1ps
// Camera stimulus is a rendered RGB565 frame, not precomputed centroid input.
module motion_c_bridge_tb(input wire mcu_rx,input wire[153:0] controls,
 input wire[130:0] vision_controls,input wire[31:0] camera_frame,
 input wire[2:0] loop_controls,
 output wire[104:0] bridge_sample,output wire[65:0] vision_status,
 output wire[34:0] loop_status);
 // Additional 10 MHz parameter coverage; UART remains 115200 baud.
 // This is a simulation clock, never a claim about the board oscillator.
 reg clk=0,camera_clk=0;always #50 clk=~clk;always #70 camera_clk=~camera_clk;
 reg old_camera=0,busy=0;reg[9:0] x=0;reg[8:0] y=0;reg[31:0] seq=0;
 always @(posedge camera_clk)begin
  old_camera<=vision_controls[1];
  if(!vision_controls[2])begin busy<=0;x<=0;y<=0;end
  else if(vision_controls[1]&&!old_camera&&!busy)begin busy<=1;x<=0;y<=0;seq<=camera_frame;end
  else if(busy)begin
   if(x==31)begin x<=0;if(y==23)begin y<=0;busy<=0;end else y<=y+1;end else x<=x+1;
  end
 end
 wire hit=x>=10&&x<=17&&y>=8&&y<=15&&!loop_controls[2];
 wire[15:0] rgb=hit?16'hf800:16'h0000;
 wire result,complete,target;wire[18:0] pixels;wire[27:0] sx,sy;
 wire[9:0] xmin,xmax;wire[8:0] ymin,ymax;
 red_frame_stats #(.WIDTH(32),.HEIGHT(24)) stats(camera_clk,vision_controls[2],busy,
 busy&&x==0&&y==0,busy&&x==31&&y==23,rgb,x,y,result,complete,target,pixels,sx,sy,xmin,ymin,xmax,ymax);
 wire[218:0] snapshot={8'd1,16'd32,16'd24,seq,seq,complete,target,pixels,sx,sy,xmin,ymin,xmax,ymax};
 wire tx,pc_tx,owner,fault,stopped,active;wire[3:0] state;
 wire[31:0] accepted,cdrop,mdrop;wire[15:0] pan,tilt;wire[1:0] mask;
 wire[31:0] status={accepted[15:0],7'b0,mask,stopped,fault,owner,state};
 reg[31:0] count=0,errors=0;reg[7:0] last=0;
 wire[7:0] rd;wire rv,re,rb;
 assign bridge_sample={count,last,errors,status,tx};
 assign vision_status={cdrop,mdrop,fault,active};
 wire la,lf,centered;wire[31:0] fc;
 assign loop_status={fc,centered,lf,la};
 // Signs are explicit fixture calibration, NOT the real mounting direction.
 zynq_gimbal1_loop #(.CLOCK_HZ(10000000),.PAN_SIGN(1),.TILT_SIGN(1)) dut(clk,controls[0],camera_clk,vision_controls[2],
 controls[1],controls[2],controls[4],loop_controls[0],loop_controls[1],controls[150:23],
 controls[151],controls[152],controls[153],mcu_rx,
 vision_controls[0],vision_controls[66:3],vision_controls[130:67],result,snapshot,
 pc_tx,tx,owner,fault,stopped,active,state,accepted,pan,tilt,mask,cdrop,mdrop,la,lf,centered,fc);
 uart_rx monitor(clk,controls[0],mcu_rx,rd,rv,re,rb);
 defparam monitor.CLOCK_HZ=10000000;
 always @(posedge clk)if(controls[0])begin
 if(rv)begin count<=count+1;last<=rd;end
 if(re)errors<=errors+1;
 end
endmodule
