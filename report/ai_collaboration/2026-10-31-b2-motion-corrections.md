# B2 engineering corrections

- A passing RTL simulation and routed timing report were insufficient: an independent
  functional-netlist decoder exposed TX stop-bit/data corruption. Keep the failure,
  repair the TX data handshake with registered prefetch, and rerun unchanged assertions.
- Do not infer ACK success from LF. Verify CRC, session, sequence, request CRC,
  operation, result/stage, targets and register mask; mismatches cannot renew authority.
- Preserve existing v15 decimal sequence acceptance (including leading zeros),
  rather than narrowing the original protocol in optional metadata parsing.
- Resolve Python source paths before hashing when a Windows drive alias is used.
- A 100MHz OOC constraint is a test assumption, not measured board clock evidence.
- Register snapshots establish software/register state, never servo position or power removal.

Only offline compilation, simulation, repository inspection and Git operations are in scope.

- A routed-netlist run printed PASS after259seconds but exceeded a240-second
  runner budget. Preserve exit1 and repeat unchanged simulation with600seconds;
  do not silently reinterpret a timeout as an accepted automated run.
