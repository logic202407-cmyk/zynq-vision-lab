# Offline XSim + OOC implementation. No hardware, bitstream or pin assignments.
# Run in a fresh repository-external ASCII D-drive directory.
set root [file normalize [file join [file dirname [info script]] ..]]
set stage [pwd]
set ::env(TEMP) [file join $stage temp]
set ::env(TMP) $::env(TEMP)
file mkdir $::env(TEMP)
create_project epoch_allocator [file join $stage epoch-project] -part xc7z100ffg900-2
add_files $root/src/rtl/epoch_qid_allocator.v
add_files -fileset sim_1 $root/sim/epoch_qid_allocator_tb.v
set_property top epoch_qid_allocator [current_fileset]
set_property top epoch_qid_allocator_tb [get_filesets sim_1]
set_property target_simulator XSim [current_project]
set_property xsim.simulate.runtime 25us [get_filesets sim_1]
update_compile_order -fileset sim_1
launch_simulation -simset sim_1 -mode behavioral
close_sim
synth_design -top epoch_qid_allocator -mode out_of_context -part xc7z100ffg900-2
create_clock -name reference_only -period 20 [get_ports clk]
opt_design
place_design
route_design
report_drc -file [file join $stage epoch-drc.rpt]
report_timing_summary -report_unconstrained -file [file join $stage epoch-timing.rpt]
report_utilization -file [file join $stage epoch-utilization.rpt]
write_checkpoint [file join $stage epoch-routed.dcp]
puts EPOCH_OFFLINE_COMPLETE_NO_BITSTREAM_OR_HARDWARE
