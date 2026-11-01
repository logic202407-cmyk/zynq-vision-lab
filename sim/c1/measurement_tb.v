`timescale 1ns/1ps
module measurement_tb;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,capture=0,urgent=0,target=1,complete=1;reg[31:0] seq=1;
 wire[7:0] data,rxdata;wire valid,ready,busy,done,tx,txbusy,txdone,rv,fe,rb;
 wire[31:0] dropped;integer fd,n=0;integer k;
 vision_measurement_tx dut(clk,rst,capture,urgent,8'd0,8'd1,64'd1,seq,32'd0,1'b0,complete,target,
 16'd640,16'd480,19'd2,28'd60,28'd80,10'd10,9'd20,10'd50,9'd60,data,valid,ready,busy,done,dropped);
 uart_tx_8n1 #(.CLOCK_HZ(100000000)) txcore(clk,rst,1'b0,valid,data,ready,tx,txbusy,txdone);
 uart_rx #(.CLOCK_HZ(100000000)) rxcore(clk,rst,tx,rxdata,rv,fe,rb);
 always @(posedge clk)begin
  if(fe)$fatal(1,"UART frame error");
  if(rv)begin $fwrite(fd,"%02x\n",rxdata);n=n+1;end
 end
 task send;begin @(negedge clk);capture=1;@(negedge clk);capture=0;end endtask
 initial begin
  fd=$fopen("uart-bytes.hex","w");#100;rst=1;urgent=1;send();#100;
  if(busy||dropped!=1)$fatal(1,"urgent traffic not prioritized");
  urgent=0;send();#100;send();if(dropped!=2)$fatal(1,"busy overwrite");
  wait(n==112);wait(!busy&&!txbusy);seq=2;target=0;send();
  wait(n==224);wait(!busy&&!txbusy);seq=3;target=1;complete=0;send();
  wait(n==336);wait(!busy&&!txbusy);#100;
  if(tx!==1)$fatal(1,"idle polarity");
  $fclose(fd);$display("C1_MEASUREMENT_PASS 3 packets 336 UART bytes; urgent/busy drops");$finish;
 end
 initial begin #100000000;$fatal(1,"watchdog");end
endmodule
