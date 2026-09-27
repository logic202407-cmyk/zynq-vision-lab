# Red-square preview threshold trial

The user placed a red square in view of the live OV5640 camera while the real PC viewer remained open. The viewer was receiving vendor UDP frames and displayed the actual scene, not its simulation source. A screenshot of the visible viewer was inspected locally; no screenshot or private room image is included in this public repository.

## Method

- Sample the viewer's displayed 640×480 image from a Windows screen capture. Windows displayed it at 125% scaling; the 800×600 screen region was reduced to 640×480 with nearest-neighbor sampling. Quantize displayed RGB888 channels to RGB565 fields with `R >> 3`, `G >> 2`, `B >> 3`.
- Mark the approximate red-square screen region as `x=255..389, y=20..199` for this trial only. It is a manual region of interest, not a saved pixel-level ground-truth mask.
- Compare the original synthetic-only predicate (`R5 >= 24`, `G6 <= 20`, `B5 <= 12`) with candidate (`R5 >= 24`, `G6 <= 30`, `B5 <= 22`). Representative square-center displayed RGB888 was `(230, 105, 139)`, quantizing to `(R5,G6,B5)=(28,26,17)`.

## Observed results

The original predicate selected zero pixels in the first screen sample. The candidate selected 20,189 pixels, all within the approximate square region, with bounding box `(262,24,383,193)`. Two subsequent samples under the same setup selected 20,231 and 20,216 pixels, with the same bounding box and no selected pixels outside that region. These are observations on a **rendered screen proxy**, not on retained raw RGB565 datagrams. The full red square occupies a larger area than the selected mask because edge highlights and shaded pixels vary.

## Decision and limits

The software reference now uses the candidate thresholds so its test predicate at least includes the observed red square under this lighting. This is not a frozen detection threshold or evidence that an FPGA module works. Screen scaling, display conversion, exposure, target color, shadows and different backgrounds can change results. Next, capture an authorized raw RGB565 frame or controlled test pattern, establish a true mask/coordinate reference, and compare the software and future PL outputs on those same bytes. Do not infer success from visually similar frames taken at different times.
