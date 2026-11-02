# Standalone full reset-context audit; no pins, no bitstream or hardware.
set root [file normalize [file join [file dirname [info script]] ..]]
if {[info exists ::env(C1_AUDIT_ROOT)]} {set root [file normalize $::env(C1_AUDIT_ROOT)]}
create_project -in_memory reset_audit -part xc7z100ffg900-2
foreach f {uart_tx_8n1 uart_rx zynq_motion_s1 vision_measurement_tx vision_snapshot_cdc uart_line_queue uart_line_scheduler measurement_nonce_observer measurement_session zynq_vision_link c1_observation_link} {read_verilog $root/src/rtl/${f}.v}
read_verilog $root/sim/c1/reset_cdc_audit_top.v
synth_design -top reset_cdc_audit_top -mode out_of_context -part xc7z100ffg900-2
create_clock -name system -period 20 [get_ports clk_50m]
create_clock -name camera -period 20 [get_ports cam_pclk]
source $root/build/c1_cdc_constraints.tcl
c1_mailbox_constraints c1_observation/link/cdc 20
report_cdc -details -file reset_cdc.rpt
report_timing_summary -report_unconstrained -file reset_timing.rpt
report_utilization -file reset_utilization.rpt
write_checkpoint -force reset_audit.dcp
puts RESET_CONTEXT_SYNTH_COMPLETE
if {[info exists ::env(C1_AUDIT_ROUTE)] && $::env(C1_AUDIT_ROUTE)} {
 opt_design
 place_design
 route_design
 report_cdc -details -file routed_cdc.rpt
 report_bus_skew -file routed_bus_skew.rpt
 report_drc -file routed_drc.rpt
 report_timing_summary -report_unconstrained -file routed_timing.rpt
 write_checkpoint -force reset_audit_routed.dcp
 puts RESET_CONTEXT_ROUTE_COMPLETE_NO_BITSTREAM
}
