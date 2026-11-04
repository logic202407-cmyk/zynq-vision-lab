# Offline OOC synthesis only. No hardware manager, pins, or bitstream.
set root [file normalize [file join [file dirname [info script]] ..]]
foreach f {uart_tx_8n1 uart_rx zynq_motion_s1_guarded vision_measurement_tx vision_snapshot_cdc uart_line_queue uart_line_scheduler measurement_nonce_observer measurement_session zynq_vision_link_guarded c1_two_axis_step_gate_v2 c1_two_axis_step_link_guarded} {
 read_verilog [file join $root src rtl ${f}.v]
}
synth_design -top c1_two_axis_step_link_guarded -part xc7z100ffg900-2 -mode out_of_context
create_clock -name candidate_sys -period 20 [get_ports clk]
create_clock -name candidate_camera -period 20 [get_ports camera_clk]
source [file join $root build c1_cdc_constraints.tcl]
c1_mailbox_constraints link/cdc 20
set latches [get_cells -hier -filter {REF_NAME =~ LD*}]
if {[llength $latches]} {error "Unexpected latches: $latches"}
report_utilization -file guarded_utilization.rpt
report_drc -file guarded_drc.rpt
report_timing_summary -report_unconstrained -file guarded_timing.rpt
report_cdc -details -file guarded_cdc.rpt
puts TWO_AXIS_GUARDED_OOC_SYNTH_PASS_NO_BITSTREAM
