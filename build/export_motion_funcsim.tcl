# Offline functional-netlist export only. Run after check_motion_s1.tcl.
open_checkpoint motion_ooc.dcp
write_verilog -force -mode funcsim motion_func.v
close_design
