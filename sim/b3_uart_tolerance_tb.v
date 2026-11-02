`timescale 1ns/1ps
// Independent timing stimulus; no production parameters are modified.
module b3_uart_tolerance_tb;
 real half=5.0,mbit=8687.5,relative;
 reg clk=0;always #(half) clk=~clk;
 reg rst=0,valid=0,rxline=1;reg[7:0] data=0;
 wire ready,tx,busy,done,rv,re,rb;wire[7:0] rd;
 uart_tx_8n1 #(.CLOCK_HZ(100000000)) t(clk,rst,1'b0,valid,data,ready,tx,busy,done);
 uart_rx #(.CLOCK_HZ(100000000)) r(clk,rst,rxline,rd,rv,re,rb);
 integer fppm,mppm,fi,mi,n,b,tn=0,rn=0,te=0,ree=0,fe=0,cases=0,required_fail=0,fh,wirelog;
 integer fp[0:4];integer mp[0:4];reg active=0;reg[7:0] v;integer votes,k;
 function[7:0] pattern;input integer x;
 begin case(x%8) 0:pattern=0;1:pattern=255;2:pattern=85;3:pattern=170;4:pattern=13;5:pattern=10;6:pattern="s";default:pattern="t";endcase end
 endfunction
 always @(posedge clk) if(rst&&active) begin
 if(rv) begin if(rd!==pattern(rn)) ree=ree+1;rn=rn+1;end
 if(re) fe=fe+1;
 end
 // Three samples around each center; simplified USART16 model, not silicon IP.
 initial forever begin
 @(negedge tx);
 if(rst&&active) begin
 v=0;#(mbit*0.5);
 if(tx!==0) te=te+1;
 for(k=0;k<8;k=k+1) begin
 #(mbit*(k==0?0.9375:0.875));votes=tx;#(mbit*0.0625);votes=votes+tx;#(mbit*0.0625);votes=votes+tx;
 v[k]=(votes>=2);
 end
 #(mbit*0.9375);
 if(v!==pattern(tn)||tx!==1) te=te+1;
 $fwrite(wirelog,"%0d,%0d,%0d,%0d,%0d\n",cases,tn,pattern(tn),v,tx!==1);
 tn=tn+1;
 end
 end
 task send_mcu;input[7:0] x;input bad;integer j;
 begin rxline=0;#(mbit);for(j=0;j<8;j=j+1) begin rxline=x[j];#(mbit);end rxline=!bad;#(mbit);rxline=1;end endtask
 task run_case;input integer f,m;input integer count;
 begin
 active=0;rst=0;rxline=1;valid=0;#200;
 fppm=f;mppm=m;half=5.0/(1.0+f/1000000.0);mbit=8687.5/(1.0+m/1000000.0);
 relative=(8687.5/8680.0)*(1.0+f/1000000.0)/(1.0+m/1000000.0)-1.0;
 tn=0;rn=0;te=0;ree=0;fe=0;rst=1;active=1;#1000;
 fork
 begin for(n=0;n<count;n=n+1) begin @(negedge clk);data=pattern(n);valid=1;@(negedge clk);valid=0;wait(done);end end
 begin for(b=0;b<count;b=b+1) send_mcu(pattern(b),0);end
 join
 #(mbit*12);active=0;
 $fwrite(fh,"%0d,%0d,%0d,%f,%f,%f,%0d,%0d,%0d,%0d,%0d\n",cases,f,m,half*1736,mbit,relative*100,tn,rn,te,ree,fe);
 if(relative>=-0.02001&&relative<=0.02001&&(te||ree||fe||tn!=count||rn!=count)) required_fail=required_fail+1;
 cases=cases+1;
 end endtask
 initial begin
 fh=$fopen("matrix.csv","w");wirelog=$fopen("mcu_bytes.csv","w");
 $fwrite(fh,"case,fpga_ppm,mcu_ppm,fpga_bit_ns,mcu_bit_ns,relative_percent,tx_count,rx_count,tx_errors,rx_errors,frame_errors\n");
 fp[0]=-20000;fp[1]=-10000;fp[2]=0;fp[3]=10000;fp[4]=20000;
 for(fi=0;fi<5;fi=fi+1)for(mi=0;mi<5;mi=mi+1)run_case(fp[fi],fp[mi],32);
 // exact nominal relative +/-2%, plus a wider failure-boundary survey.
 run_case(0,21289,32);run_case(0,-18761,32);
 for(fi=-80000;fi<=80000;fi=fi+10000)run_case(0,fi,32);
 run_case(0,0,256);
 rst=0;#200;rst=1;active=1;rn=0;ree=0;fe=0;
 rxline=0;#1000;rxline=1;#(mbit*12);if(rn||fe)$fatal(1,"false start accepted");
 send_mcu(8'h55,1);#(mbit*15);if(fe!=1||rn!=0)$fatal(1,"bad stop not detected");
 send_mcu(0,0);#(mbit*12);if(rn!=1||ree)$fatal(1,"RX failed resynchronization");
 $fclose(fh);$fclose(wirelog);
 if(required_fail)$fatal(1,"required relative2percent cases failed %0d",required_fail);
 $display("B3_UART_PASS cases=%0d false-start bad-stop recovery PASS",cases);$finish;
 end
 initial begin #200000000;$fatal(1,"watchdog");end
endmodule
