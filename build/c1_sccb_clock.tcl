# Source guard runs before project creation. No clock groups, delay guesses or waivers.
proc c1_sccb_clock {} {
 if {[get_property PART [current_design]] ne {xc7z100ffg900-2}} {error {Wrong device}}
 set source [get_pins -quiet u_i2c_dri/dri_clk_reg/C]
 set target [get_pins -quiet u_i2c_dri/dri_clk_reg/Q]
 if {[llength $source]!=1 || [llength $target]!=1} {error {Reviewed divider pin not found}}
 set parent [get_clocks -of_objects $source]
 if {[llength $parent]!=1 || abs([get_property PERIOD $parent]-20.0)>0.001} {error {Unreviewed SCCB parent clock}}
 if {[llength [get_clocks -of_objects $target]]!=0} {error {SCCB clock already defined; review instead of overwriting}}
 create_generated_clock -name c1_sccb_driver -source $source -divide_by 50 $target
 if {abs([get_property PERIOD [get_clocks c1_sccb_driver]]-1000.0)>0.001} {error {SCCB clock period mismatch}}
 puts SCCB_GENERATED_CLOCK_BOUND_TO_REVIEWED_SOURCE
}
