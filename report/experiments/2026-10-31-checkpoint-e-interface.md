# Checkpoint E: vision interface review and plan

Status: planned, documentation and offline source review only. C remains pending.
The [M1/S1 boundary proposal](../../docs/vision_uart_interface_plan_v1.md) defines
source identity, same-frame matching, bounds, time/sequence/CRC strategy and
future test verdicts. It is not a wire implementation or a board result.

Reviewed source inputs: existing PL mask/filter/stats/header RTL,
`src/interface_contract.md`, PC `vendor_udp.py`/`pl_compare.py`, Python reference,
and the S1 safety candidate. The [review manifest](../evidence/checkpoint_e/manifest.json)
records exact versions/file SHA-256 and source parent commit. Actual repository
and existing-test exits are in [checks.txt](../evidence/checkpoint_e/checks.txt).
The post-commit receipt records the actual E commit without a circular self-hash.

Important findings: frame N header reports N-1; sequence/metadata currently lacks
boot identity and row integrity; PC local indexing/display smoothing is not PL
measurement; 640x480 offsets cannot be fed unchanged into the 160x120 legacy
range; no physical angle measurement exists. None of those source paths changed.

M1's proposed 64-byte schema distinguishes PL from PC_REFERENCE, uses source
session and distinct packet/frame sequences, reserves explicit mask/config ID,
and CRC32. Receiver-local age is separate from unsynchronized source ticks.
Current S1 motion commands lack a measurement-lineage ACK: the plan records that
extension as future work. No measurements renew/re-arm a control lease.

No private frame, unique device ID, vendor source, credential or license is
published. No UART/JTAG/Flash/power/motion operation occurred. The next permitted
step is a design review; physical integration still requires the operator's
separate authorization and C/electrical prerequisites.
