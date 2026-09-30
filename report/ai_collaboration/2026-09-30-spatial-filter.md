# Spatial-filter verification corrections

- The original 6×6 spatial bench checked a solid patch and all-red borders,
  but did not exercise a neighborhood with exactly five votes. Explicit
  four- and five-vote scenes were added before accepting the filter. A private
  six-vote mutation then failed at `five-vote threshold mismatch`.
- A header version was added for the filtered mask rather than interpreting
  filtered counts as the old threshold-only count. RTL serialization and the
  host parser were tested for both supported versions; unknown versions are
  rejected. The viewer labels the selected PL mode.
- Current JTAG discovery and a UDP start-command probe found no hardware
  target or video. Implementation and simulation proceeded locally, while
  the spatial filter's board status remains unverified.
- Windows reported problem code 10 for the FTDI USB download device. A
  targeted restart attempt returned `Access is denied`; manual USB reconnection
  was requested. The bound camera socket's route was confirmed to use the
  wired adapter, even though Wi-Fi is on the same subnet.
