# Read-only JTAG discovery. Do not program or refresh a device.
set exit_code 0
set target_open 0

if {[catch {
    open_hw_manager
    connect_hw_server -url localhost:3121
    set targets [get_hw_targets]
    puts "PROBE_TARGET_COUNT=[llength $targets]"
    foreach target $targets {
        puts "PROBE_TARGET=$target"
        if {[catch {
            open_hw_target $target
            set target_open 1
            set devices [get_hw_devices]
            puts "PROBE_DEVICE_COUNT=[llength $devices]"
            foreach device $devices {
                puts "PROBE_DEVICE=$device"
                foreach property {PART IDCODE IR_LENGTH} {
                    if {![catch {get_property $property $device} value]} {
                        puts "PROBE_${property}=$value"
                    }
                }
            }
            close_hw_target
            set target_open 0
        } target_error]} {
            puts "PROBE_TARGET_ERROR=$target_error"
            if {$target_open} {
                catch {close_hw_target}
                set target_open 0
            }
            set exit_code 1
        }
    }
    if {[llength $targets] == 0} {
        set exit_code 1
    }
} error]} {
    puts "PROBE_ERROR=$error"
    set exit_code 1
}

if {$target_open} {catch {close_hw_target}}
catch {disconnect_hw_server}
catch {close_hw_manager}
exit $exit_code
