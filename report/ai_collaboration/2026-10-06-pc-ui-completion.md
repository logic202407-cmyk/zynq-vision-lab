# Complete the requested camera UI before returning

The user requested a working live camera UI that could identify the red paper.
After recovering the stream, the assistant initially stopped at a color
diagnostic and proposed further physical scene adjustments. That did not
complete the requested screen-level result.

The correction was to add an explicitly labelled independent PC detector,
validate it on synthetic boundary cases and actual saved/live camera images,
and leave the live UI running. Received PL fields and frozen acceptance gates
remain unchanged. Occluded inputs and absent-target observations are recorded
separately instead of being counted as successful positives.

The delivery branch excludes unrelated unpublished work and has its own
174-test receipt. See the [experiment record](../experiments/2026-10-06-pc-paper-ui.md)
for measured results and their limits.
