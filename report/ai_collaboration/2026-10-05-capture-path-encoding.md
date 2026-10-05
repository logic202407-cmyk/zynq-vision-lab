# Capture helper: Unicode path preflight gap

The helper was corrected before any packet capture started. An administrator
invocation failed when creating its guard file because a UTF-8-without-BOM
settings JSON was read without an explicit encoding by Windows PowerShell 5.1.
The private output path contained non-ASCII characters; the decoded value no
longer matched the UTF-8 value and was an illegal filesystem path.

Initial checks covered syntax, NIC uniqueness and a validation-only mode that
returned before reading/writing the actual destination. They did not establish
that the administrator execution environment could use that destination.
The check was too narrow. The fix sets `Get-Content -Encoding UTF8` for the
settings JSON and makes validation-only mode create/remove a new temporary
file in the actual output directory, using the same Windows PowerShell 5.1
executable. Reproduction and corrected path checks passed; old failures were
retained. No network settings or board configuration were changed.

Cross-process configuration encoding and destination usability must be checked
in the execution environment, separately from syntax and algorithm tests.
Passing these checks prepares a helper; only actual packet logs can establish
capture or network evidence. Private paths and screenshots are not copied here.
