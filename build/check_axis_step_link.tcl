# Offline synthesis only; reference package, no board clocks/pins or hardware.
create_project -in_memory -part xc7z100ffg900-2
read_verilog {uart_tx_8n1.v uart_rx.v zynq_motion_s1.v c1_axis_step_gate.v c1_axis_step_link.v}
synth_design -top c1_axis_step_link -part xc7z100ffg900-2 -mode out_of_context
set latches [get_cells -hier -filter {REF_NAME =~ LD*}]
if {[llength $latches] != 0} {error "Unexpected inferred latch"}
report_utilization -file utilization.rpt
report_drc -checks {MDRV-1 LUTLP-1} -file structural_drc.rpt
if {[llength [get_drc_violations -quiet -filter {NAME =~ MDRV-1* || NAME =~ LUTLP-1*}]] != 0} {error "Structural DRC failure"}
puts "AXIS_STEP_SYNTH_PASS (reference part only; no timing or board acceptance)"
close_project
