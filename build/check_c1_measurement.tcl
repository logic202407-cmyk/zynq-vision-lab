# Offline candidate only. No pins, bitstream or hardware manager.
set root [file normalize [file join [file dirname [info script]] ..]]
read_verilog [file join $root src rtl vision_measurement_tx.v]
synth_design -top vision_measurement_tx -part xc7z100ffg900-2 -mode out_of_context
create_clock -name candidate_clk -period 10 [get_ports clk]
opt_design
place_design
route_design
report_utilization -file c1_utilization.rpt
report_timing_summary -report_unconstrained -file c1_timing.rpt
report_drc -file c1_drc.rpt
write_checkpoint c1_measurement.dcp
puts C1_OOC_COMPLETE_NO_BITSTREAM
