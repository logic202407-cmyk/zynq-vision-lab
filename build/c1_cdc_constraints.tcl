# Template for a REAL enclosing design with both clocks already declared.
# Not a board XDC and never assigns pins, voltages or frequencies.
# Call c1_mailbox_constraints with the actual mailbox instance and destination period.
proc c1_mailbox_constraints {instance destination_period_ns} {
    set held [get_cells -hier -filter "NAME =~ ${instance}/holding_reg* && IS_SEQUENTIAL"]
    set captured [get_cells -hier -filter "NAME =~ ${instance}/dst_data_reg* && IS_SEQUENTIAL"]
    if {[llength $held]==0 || [llength $captured]==0} {error "CDC payload registers not found"}
    set_max_delay -datapath_only $destination_period_ns -from $held -to $captured
    set_bus_skew $destination_period_ns -from $held -to $captured
    # Cut only first stages of toggle synchronizers, not the payload or all clocks.
    foreach stem {req_sync ack_sync} {
        set first [get_pins -hier -regexp "${instance}/${stem}_reg\\\[0\\\]/D"]
        if {[llength $first]!=1} {error "CDC first stage not found: $stem"}
        set_false_path -to $first
    }
}
