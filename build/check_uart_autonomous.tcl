# Offline out-of-context implementation. NO package pins, bitstream or hardware.
# Run from a staging directory containing the three RTL sources.
set_param general.maxThreads 2
create_project -in_memory -part xc7z100ffg900-2
read_verilog {uart_tx_8n1.v uart_rx.v zynq_uart_autonomous.v}
synth_design -top zynq_uart_autonomous -part xc7z100ffg900-2 -mode out_of_context -generic CLOCK_HZ=100000000
create_clock -name candidate_clk -period 10.000 [get_ports clk]
set latch_count [llength [get_cells -hier -filter {REF_NAME =~ LD*}]]
if {$latch_count != 0} {error "Unexpected inferred latches: $latch_count"}
report_utilization -file utilization.rpt
opt_design
place_design
route_design
report_route_status -file route_status.rpt
report_drc -file drc.rpt
report_drc -checks {MDRV-1 LUTLP-1} -file structural_drc.rpt
set structural [get_drc_violations -quiet -filter {NAME =~ MDRV-1* || NAME =~ LUTLP-1*}]
if {[llength $structural] != 0} {error "Multiple driver / combinational loop violations"}
report_timing_summary -report_unconstrained -file timing.rpt
write_checkpoint -force autonomous_ooc.dcp
set result "UART_AUTONOMOUS_OOC_PASS latches=$latch_count; candidate 100MHz only; no IO timing or hardware signoff"
# A Vivado webserver session may have no stdout channel. Write an explicit
# receipt so batch and plugin execution have the same terminal verdict.
set receipt [open implementation_pass.txt w]
puts $receipt $result
close $receipt
if {[lsearch -exact [chan names] stdout]>=0} {puts $result}
close_project
set result
