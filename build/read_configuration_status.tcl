# Query current configuration state; no bitstream, reset or memory writes.
set exit_code 0
set target_open 0
if {[catch {
    open_hw_manager
    connect_hw_server -url localhost:3121
    set targets [get_hw_targets]
    puts "STATUS_TARGET_COUNT=[llength $targets]"
    if {[llength $targets] != 1} { error "Expected exactly one target" }
    open_hw_target [lindex $targets 0]
    set target_open 1
    set devices [get_hw_devices -filter {PART == xc7z100}]
    if {[llength $devices] != 1} { error "Expected exactly one XC7Z100" }
    set device [lindex $devices 0]
    if {[catch {refresh_hw_device -update_hw_probes false $device} refresh_error]} {
        puts "STATUS_REFRESH_ERROR=$refresh_error"
        set exit_code 1
    } else {
        puts "STATUS_REFRESH_OK=1"
    }
    foreach property [list_property $device] {
        if {$property eq "PART" || $property eq "PROGRAM.IS_PROGRAMMED" || [string match "REGISTER.CONFIG_STATUS*" $property]} {
            if {![catch {get_property $property $device} value]} {
                puts "STATUS_${property}=$value"
            }
        }
    }
} query_error]} {
    puts "STATUS_ERROR=$query_error"
    set exit_code 1
}
if {$target_open} {catch {close_hw_target}}
catch {disconnect_hw_server}
catch {close_hw_manager}
exit $exit_code
