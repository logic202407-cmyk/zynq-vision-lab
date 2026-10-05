# Additional user-requested diagnostic retry 02

After today's formal exact100 failure, the user explicitly requested one more
test. A separate diagnostic attempt was registered before capture. The host's
wired link was Up with the preferred address, board-only route and no UDP1234
listener; no network setting was changed.

The **10.05-second probe received zero complete frames and zero payload bytes**.
Its process returned exit 0, but the real-video gate is **FAIL**. The planned
diagnostic 100-pair comparison was therefore **not_run**. This result does not
replace the earlier 99-pair failed formal window or the earlier 292-frame probe.

One bounded read-only JTAG query used the unchanged default-clock script and
an owned temporary hardware server. It returned exit 0, target count 1,
XC7Z100, refresh OK and **EOS/internal DONE/pin DONE all 1**. This is an actual
later configuration observation even though the preceding probe had no video.
No programming, reset or clock change was performed. The owned server was
stopped, its absence checked and UDP1234 had no listener at completion.
[Actual query observations, gate and release receipt](2026-10-05-v1-diagnostic-retry-02.json)
record the available register values separately from unknown fields. No cause
is inferred from the host network state or earlier successful configuration.

This is an additional diagnostic attempt, not a new passing P0 scene, sustained
30-second test, v2 hardware run or whole-system acceptance. Full device logs and
host paths remain private.
