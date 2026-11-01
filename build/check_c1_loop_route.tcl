# Run in the same offline session after check_c1_loop.tcl. No bitstream.
opt_design
place_design
phys_opt_design
route_design
report_timing_summary -report_unconstrained -file loop_routed_timing.rpt
report_cdc -details -file loop_routed_cdc.rpt
report_drc -file loop_routed_drc.rpt
report_utilization -file loop_routed_utilization.rpt
report_bus_skew -file loop_bus_skew.rpt
puts C1_LOOP_ROUTE_COMPLETE_NO_BITSTREAM
