# Full board offline evidence

The source-equivalent vendor top/XDC and latest C1 were prepared in a fresh
private D: directory, then synthesized and routed with Vivado 2024.2. Original
reports have exact SHA-256 receipts in the private result package. Public text
copies redact host identity and normalize newlines; their separate manifest
hashes describe these published bytes. No license, vendor source, DCP/LTX,
device identifier or bitstream is published.

`board-audit.json` summarizes the complete routed top. `sccb-clock-audit.json`
summarizes the generated-clock-only experiment on the same DCP without reroute.
Both retain board_signoff=false. `clock-first-failure.txt` preserves the initial
metadata-guard error. This tool failure is distinct from a design failure.
Synthetic command IDs in C tests and tool-generated clock assumptions are not
physical observations. All hardware actions are empty.
