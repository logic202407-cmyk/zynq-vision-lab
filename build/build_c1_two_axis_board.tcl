# Run only in a NEW private working directory containing prepared vendor/.
# Generates a candidate, never programs hardware. Vendor HDL remains private.
set repo [file normalize [file join [file dirname [info script]] ..]]
set private [file normalize [file join [pwd] vendor]]
if {![file exists $private/source-sha256.json]} {error {Prepare private vendor integration first}}
set c1_python D:/Python312/python.exe
if {[info exists ::env(C1_PYTHON)]} {set c1_python $::env(C1_PYTHON)}
# Vivado exports its bundled Python environment; isolate the selected interpreter.
puts [exec $c1_python -I $repo/tools/c1_sccb_contract.py --vendor $private --output [file join [pwd] clock-contract.json]]
create_project c1_two_axis ./project -part xc7z100ffg900-2
set_property target_language Verilog [current_project]
set_property simulator_language Mixed [current_project]
foreach d [list $private/rtl $private/rtl/arp $private/rtl/udp $private/rtl/ov5640 $private/rtl/gmii_to_rgmii] {
 add_files [glob $d/*.v]
}
add_files -fileset constrs_1 $private/ov5640_udp_pc.xdc
foreach f [glob $private/ip/*/*.xci] {import_ip $f}
upgrade_ip [get_ips]
create_ip -name vio -vendor xilinx.com -library ip -version 3.0 -module_name c1_observation_vio
set_property -dict {CONFIG.C_NUM_PROBE_IN 2 CONFIG.C_NUM_PROBE_OUT 3 CONFIG.C_PROBE_IN0_WIDTH 32 CONFIG.C_PROBE_IN1_WIDTH 32 CONFIG.C_PROBE_OUT0_WIDTH 10 CONFIG.C_PROBE_OUT1_WIDTH 128 CONFIG.C_PROBE_OUT2_WIDTH 64 CONFIG.C_PROBE_OUT0_INIT_VAL 0x000 CONFIG.C_PROBE_OUT1_INIT_VAL 0x0 CONFIG.C_PROBE_OUT2_INIT_VAL 0x0} [get_ips c1_observation_vio]
generate_target all [get_ips]
set_property top ov5640_udp_pc [current_fileset]
update_compile_order -fileset sources_1
report_ip_status -file ip_status.rpt
launch_runs synth_1 -jobs 2
wait_on_run synth_1
if {[get_property PROGRESS [get_runs synth_1]] ne {100%}} {error {Synthesis failed}}
open_run synth_1
source $repo/build/c1_cdc_constraints.tcl
c1_mailbox_constraints c1_observation/link/cdc 20
source $repo/build/c1_sccb_clock.tcl
c1_sccb_clock
report_clocks -file clocks.rpt
report_cdc -details -file synthesis_cdc.rpt
report_drc -file synthesis_drc.rpt
report_timing_summary -report_unconstrained -file synthesis_timing.rpt
# Persist reviewed timing constraints for implementation. Only payload path and
# toggle first stages are excepted; no wholesale asynchronous clock groups.
write_xdc -force -type timing c1_synth_timing.xdc
close_design
add_files -fileset constrs_1 c1_synth_timing.xdc
set_property USED_IN_SYNTHESIS false [get_files c1_synth_timing.xdc]
launch_runs impl_1 -to_step route_design -jobs 2
wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] ne {100%}} {error {Implementation failed}}
open_run impl_1
report_timing_summary -report_unconstrained -file routed_timing.rpt
report_cdc -details -file routed_cdc.rpt
report_bus_skew -file routed_bus_skew.rpt
report_drc -file routed_drc.rpt
report_utilization -file routed_utilization.rpt
check_timing -verbose -file routed_check_timing.rpt
report_clocks -file routed_clocks.rpt
write_checkpoint -force c1_two_axis_routed.dcp
write_debug_probes -force c1_two_axis.ltx
set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
set_property BITSTREAM.CONFIG.USR_ACCESS 0xc104d121 [current_design]
write_bitstream -force c1_two_axis.bit
puts C1_TWO_AXIS_BUILT_NO_PROGRAMMING
