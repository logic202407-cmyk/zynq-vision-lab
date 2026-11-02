# Offline report-only experiment on a private routed checkpoint.
# Derivation applies ONLY to the reviewed vendor top: CLK_FREQ=50_000_000,
# I2C_FREQ=250_000; clk_divide=50; toggle every 25 parent edges => divide_by 50.
# This is a source-derived clock declaration, not a frequency measurement.
# Use a NEW empty working directory. No bitstream or hardware API is used.
if {[llength $argv] != 1} {error {Expected one private routed DCP path}}
open_checkpoint [lindex $argv 0]
# A reopened DCP can take its filename as the design object's NAME. Check
# device and enclosing board structure rather than assuming that metadata is top.
if {[get_property PART [current_design]] ne {xc7z100ffg900-2}} {error {Wrong device}}
if {[llength [get_ports -quiet {sys_clk_p cam_pclk eth_rxc c1_mcu_rx c1_mcu_tx c1_pc_tx}]] != 6 || [llength [get_cells -quiet {u_i2c_dri c1_observation u_img_data_pkt}]] != 3} {error {Reviewed board structure not found}}
set root_pin [get_pins -quiet u_i2c_dri/dri_clk_reg/C]
set generated_pin [get_pins -quiet u_i2c_dri/dri_clk_reg/Q]
if {[llength $root_pin] != 1 || [llength $generated_pin] != 1} {error {Reviewed divider register not found}}
set parent_clock [get_clocks -of_objects $root_pin]
if {[llength $parent_clock] != 1} {error {Ambiguous divider source clock}}
if {abs([get_property PERIOD $parent_clock]-20.0)>0.001} {error {Expected declared 50 MHz parent}}
if {[llength [get_clocks -of_objects $generated_pin]] != 0} {error {Divider clock already constrained; review before overriding}}
create_generated_clock -name sccb_dri_candidate -source $root_pin -divide_by 50 $generated_pin
report_clocks -file candidate_clocks.rpt
report_timing_summary -report_unconstrained -file routed_timing.rpt
report_cdc -details -file routed_cdc.rpt
report_drc -file candidate_drc.rpt
check_timing -verbose -file candidate_check_timing.rpt
puts SCCB_CLOCK_AUDIT_COMPLETE_NO_HARDWARE_NO_REROUTE
exit
