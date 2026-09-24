# Read-only catalog query. A listed part does not identify the physical board.
puts "PROBE_VIVADO=[version -short]"
foreach part {xc7z035ffg900-2 xc7z045ffg900-2 xc7z100ffg900-2} {
    set matches [get_parts -quiet $part]
    puts "PROBE_PART=$part COUNT=[llength $matches]"
}
exit 0
