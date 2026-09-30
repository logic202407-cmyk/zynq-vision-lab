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
  was initially requested. The user then authorized remote administrator
  approval, and targeted USB restarts cleared code 10. USB status alone did
  not restore the camera: both candidate and previous camera configurations
  failed with startup `LOW`. Discovery subsequently became intermittent.
  The bound camera socket's route was confirmed to use the wired adapter,
  even though Wi-Fi is on the same subnet.
- The generic 250 kHz setting was accepted before opening the cable but
  failed when applied afterward. The script did not reach programming or
  voltage acquisition; this is not a successful slow-clock retry or a
  measured supply problem. An XSDB probe was stopped without executing reset.
- Compression was generated from the previous routed checkpoint to reduce
  transfer size, without changing image-processing logic. The default
  license selection initially failed; an explicit process-local selection
  of the existing working license allowed bitgen to finish. Configuration
  was not retried because the final approved USB restart returned 3010,
  explicitly requiring a Windows computer restart. At this stage the computer
  had not been rebooted; the user subsequently saved other work and explicitly
  authorized that restart. See the
  [recovery record](../experiments/2026-09-30-jtag-recovery.md).
- The host restart was verified, but a compressed previous camera download
  still failed with startup LOW. A guarded PCAP_MODE change read back correctly;
  later attempts failed before programming and cable discovery became empty.
  These different failure stages must not be combined into one diagnosed cause.
- An XSDB launcher returned process exit code 0 while the script printed a
  configuration-request error. Acceptance therefore requires explicit success
  markers and readable EOS/DONE status, followed by real camera reception.
  USB code 0 and an internal voltage snapshot do not meet that gate. The
  [post-reboot record](../experiments/2026-09-30-jtag-post-reboot.md) preserves
  the sequence and the pending physical power-cycle boundary.
