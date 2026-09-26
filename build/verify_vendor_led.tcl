# In-process local rebuild of the reviewed vendor one-key/one-LED reference.
# Usage: vivado -mode batch -source build/verify_vendor_led.tcl -nojournal -nolog -tclargs <source_dir> <output_dir>
# Does not open hardware or program the board. Source stays outside the public repository.
if {$argc != 2} {
    error "Expected source_dir and output_dir"
}

set source_dir [file normalize [lindex $argv 0]]
set output_dir [file normalize [lindex $argv 1]]
set verilog_file [file join $source_dir led.v]
set constraint_file [file join $source_dir led.xdc]
if {![file exists $verilog_file] || ![file exists $constraint_file]} {
    error "Missing reviewed vendor LED source or constraints"
}
file mkdir $output_dir
cd $output_dir

# Keep all implementation work in this process on hosts where child Vivado jobs are restricted.
set_param general.maxThreads 1
create_project -in_memory -part xc7z100ffg900-2
read_verilog $verilog_file
read_xdc $constraint_file
synth_design -top led -part xc7z100ffg900-2
puts "VENDOR_LED_SYNTH_COMPLETE=1"
opt_design
place_design
route_design
report_timing_summary -file [file join $output_dir led_timing_summary.rpt]
report_utilization -file [file join $output_dir led_utilization.rpt]
write_bitstream -force [file join $output_dir led.bit]
puts "VENDOR_LED_BITSTREAM=[file join $output_dir led.bit]"
close_project
exit 0
