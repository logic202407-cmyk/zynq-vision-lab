# Offline OOC check, candidate clocks and synthetic direction signs only.
# Never opens hardware manager, writes a bitstream, or assigns board pins.
set root [file normalize [file join [file dirname [info script]] ..]]
foreach f {uart_tx_8n1 uart_rx zynq_motion_s1 vision_measurement_tx vision_snapshot_cdc uart_line_queue uart_line_scheduler measurement_nonce_observer measurement_session zynq_vision_link gimbal1_visual_loop zynq_gimbal1_loop} {
 read_verilog [file join $root src rtl ${f}.v]
}
synth_design -top zynq_gimbal1_loop -part xc7z100ffg900-2 -mode out_of_context -generic {PAN_SIGN=1 TILT_SIGN=1}
create_clock -name candidate_sys -period 10 [get_ports clk]
create_clock -name candidate_camera -period 14 [get_ports camera_clk]
source [file join $root build c1_cdc_constraints.tcl]
c1_mailbox_constraints link/cdc 10
set latches [get_cells -hier -filter {REF_NAME =~ LD*}]
if {[llength $latches]} {error "Unexpected latches: $latches"}
report_utilization -file loop_utilization.rpt
report_drc -file loop_drc.rpt
report_timing_summary -report_unconstrained -file loop_timing.rpt
puts C1_LOOP_SYNTH_PASS_NO_BITSTREAM
