# Offline candidate clocks, NOT measured board clocks. No pins/bitstream/JTAG.
set root [file normalize [file join [file dirname [info script]] ..]]
foreach f {uart_tx_8n1 uart_rx zynq_motion_s1 vision_measurement_tx vision_snapshot_cdc uart_line_queue uart_line_scheduler measurement_nonce_observer measurement_session zynq_vision_link} {
 read_verilog [file join $root src rtl ${f}.v]
}
synth_design -top zynq_vision_link -part xc7z100ffg900-2 -mode out_of_context
create_clock -name candidate_sys -period 10 [get_ports clk]
create_clock -name candidate_camera -period 14 [get_ports camera_clk]
source [file join $root build c1_cdc_constraints.tcl]
c1_mailbox_constraints cdc 10
report_utilization -file link_utilization.rpt
report_cdc -details -file link_cdc.rpt
report_timing_summary -report_unconstrained -file link_timing.rpt
report_drc -file link_drc.rpt
puts C1_LINK_SYNTH_COMPLETE_NO_BITSTREAM
