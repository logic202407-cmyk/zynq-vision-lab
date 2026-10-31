# Checkpoint B: MCU-local fail-closed supervisor candidate

Status: implemented, host/register-model tested and ARM-compiled; **not flashed
or board verified**. This checkpoint follows A commit `2b9f1b3`; the preserved
baseline remains `4a254d2bd5846efccadd6d812eb0980abd28d1f6`.
No hardware interface was opened and no Flash/JTAG/power/movement action performed.

## Changes and rationale

The existing `tracking.c` PID/controller remains intact. New `safety.c/.h` owns
permission around that legacy controller; main accepts protected session frames,
not bare motion commands. Boot, stop and fault disable output. Re-arming requires
the current challenge and a deliberate seq-0 arm frame, followed by a separate
fresh positive-sequence command. Returning vision/USB traffic cannot enable PWM.

The 500 ms MCU-local lease uses UART arrival timestamps. Repeated, reordered,
old-session data and `st` do not extend it. SysTick enforces expiry independently
of the FPGA and foreground loop; UART errors, queue full, KEY and invalid pulse
range disable the timer outputs directly. The first fault cause stays latched.
GPIO outputs are forced low; the external servo supply remains a separate circuit.

Frames have CRC16 and session/sequence checks. `stop` and `st` remain available
without a valid session. Faults flush stale queues and parser state, while idle
fault loops allow a new operator session to be received. Auto mode additionally
requires fresh valid vision; invalid/lost vision is latched, not auto-resumed.

For boot replay rejection, the candidate obtains two nonzero distinct RNG words
from PLL48 while SYSCLK/PWM/UART stay HSI16. All waits and clock/seed failures
fail closed; no constant nonce fallback exists. This is a new, unflashed hardware
path and is a mandatory unpowered acceptance item. It is not an entropy-security
certificate or proof of resistance to a malicious sender.

Unchanged P0 status preserves read-only PID-workbench parsing. Separate `S1STAT`
explicitly reports safety state, first cause, nonce, sequence, FW15 and TX drops.
The previous GUI/bench motion sender has no guarded-session adapter and its raw
motion/PID writes are deliberately rejected. See the
[S1 contract](../../docs/skystar_safety_protocol_v1.md).

## Test inputs and actual results

Reproduce with `tools/check_skystar_safety.py --private-output <outside-git>
--temp <outside-git>` on one command line. The runner cannot access serial/JTAG.
It executes both actual C configurations with `-Wall -Wextra -Werror`, real
register-driver code, both ARM builds, vector/map verification, all Python tests
and repository checks. Tool/test/source SHA-256, commands, actual assertion counts,
all exits and firmware hashes are in [manifest.json](../evidence/checkpoint_b/manifest.json).
Actual logs are beside it, including [USART1](../evidence/checkpoint_b/uart1.txt),
[USART3](../evidence/checkpoint_b/uart3.txt) and
[Python](../evidence/checkpoint_b/python-tests.txt). Binaries remain outside Git
under the operator's specified root. The commit receipt is recorded after commit
in local evidence and in the GitHub/checkpoint report, avoiding a circular self-hash.

Cases include completed manual command then silence; 499/500 ms boundaries;
foreground-stalled ISR cutoff; st/duplicate heartbeat not renewing; fresh arm
without PWM; stop preserving the first fault; new valid vision after fault; old
session/sequence replay and sequence exhaustion; CRC mutation and independent
Python wire fixture; queued old bytes and partial line tails; normal slicing of
a recovery command; UART fault/overflow; KEY; output range defense; auto vision
loss/partial timeout; millisecond wrap; new boot nonce; RNG clock/seed/timeout/
zero/duplicate failures; and 1,000 deterministic malformed frames, each followed
by 32 pseudo-random bytes while checking that output remains disabled.
Legacy PID numerical vectors remain in the tests. Console expectations were
changed explicitly for the new protected protocol, not weakened to pass a failure.

Initial failures were retained and explained: a CRC signedness warning was fixed
without removing `-Werror`; the clock model was corrected to match simulated UART
arrival time; and strict old P0 parsing prompted separate safety telemetry instead
of weakening its parser. Sanitized failure history is in
[failures.txt](../evidence/checkpoint_b/failures.txt).

## Limits and next gate

Real J23 voltage, RNG behavior, clock tolerances, ISR latency, actual PWM cutoff,
power-disconnected reset and cable-loss behavior are unverified. No claim is made
for processor clock failure, permanently masked interrupts, physical power
cutoff or mechanical stopping. A software lease is not an emergency-stop circuit.
No automatic Flash write, re-arm or motion-on-reconnect occurs.

Offline B passes only if the manifest/step exits are zero. Hardware C remains
blocked pending the user's explicit authorization, independent power-disconnect
confirmation and electrical/physical prerequisites. The
[C observation sheet](../../docs/skystar_checkpoint_c_observation.md) is prepared
with pending actual-measurement fields; no physical results are prefilled.
