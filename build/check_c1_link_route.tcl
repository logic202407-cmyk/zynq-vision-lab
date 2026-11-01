# Run after check_c1_link.tcl, in the same offline session. No bitstream.
opt_design
place_design
phys_opt_design
route_design
report_utilization -file link_routed_utilization.rpt
report_cdc -details -file link_routed_cdc.rpt
report_timing_summary -report_unconstrained -file link_routed_timing.rpt
report_drc -file link_routed_drc.rpt
report_bus_skew -file link_bus_skew.rpt
puts C1_LINK_ROUTE_COMPLETE_NO_BITSTREAM
