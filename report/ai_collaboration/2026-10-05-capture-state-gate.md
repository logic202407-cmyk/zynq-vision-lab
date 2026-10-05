# Capture state gate and missing failure diagnostics

The private recovery/capture entry restored the authorized temporary wired
address and board-only route successfully. Its capture child then stopped at
the global ETW-session query gate, before starting PktMon or a video receiver.
The helper checked the command return code before preserving output, leaving
only `Cannot inspect existing ETW sessions`. This diagnostic omission is a
helper mistake; the underlying native-command failure is not established.

A later non-admin Windows PowerShell 5.1 reproduction of `logman query -ets`
returned 0. That does not reproduce the administrator failure and cannot be
used to claim a cause or working capture. Prior failed guards and receipts
remain unchanged in private storage.

The fresh helper uses the documented
[`pktmon status`](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/pktmon-status)
query for its own running state, preserving output/return code before checking
it. Only exit 0 plus an exact installed inactive-state message permits start.
Active, unknown, mixed and denied outputs stop the helper before any start/stop
operation. The same preservation order applies to component enumeration.

Validation in the actual Windows PowerShell 5.1 environment passed: six state
fixtures, three NIC-selection fixtures, syntax and the actual private output
path. These checks are not privileged execution or packet evidence. Raw logs,
captures, identities and settings remain private; the sanitized chronology and
hash receipts are linked from the
[diagnostic record](../experiments/2026-10-05-link-activity-diagnostic.md).
