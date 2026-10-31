# Candidate bridge build; requires an independently reviewed four-port XDC.
# vivado -mode batch -source build_zynq_uart_bridge.tcl -tclargs reviewed.xdc output_dir
# Does not open hardware or program a board.
if {$argc != 2} { error "Expected reviewed.xdc and output_dir" }
set constraints [file normalize [lindex $argv 0]]
if {![file isfile $constraints]} { error "Reviewed XDC not found" }
set output [file normalize [lindex $argv 1]]
set source [file normalize [file join [file dirname [info script]] ../src/rtl/zynq_uart_bridge.v]]
file mkdir $output
cd $output
create_project -in_memory -part xc7z100ffg900-2
read_verilog $source
synth_design -top zynq_uart_bridge -part xc7z100ffg900-2
read_xdc $constraints
foreach port {pc_rx pc_tx skystar_rx skystar_tx} {
    set obj [get_ports $port]
    if {[get_property PACKAGE_PIN $obj] eq "" || [get_property IOSTANDARD $obj] eq "DEFAULT"} {
        error "Missing reviewed pin/IOSTANDARD for $port"
    }
}
opt_design
place_design
route_design
report_drc -file bridge_drc.rpt
write_bitstream -force zynq_uart_bridge.bit
puts "BRIDGE_CANDIDATE_BITSTREAM_COMPLETE; board and signal integrity unverified"
close_project
exit 0
