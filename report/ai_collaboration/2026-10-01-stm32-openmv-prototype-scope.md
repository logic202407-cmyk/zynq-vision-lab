# STM32/OpenMV prototype scope corrections

Date: 2026-10-01

During repository preparation, the model initially treated an accidental
leading character in `main.c` and an older build timestamp as evidence that the
current firmware had not compiled. The contributor removed the accidental
character, rebuilt the source, and provided a fresh Keil result with 0 errors
and 0 warnings. The published record therefore uses the newer build result.

The contributor also clarified two evidence points:

- OpenMV IDE displayed approximately 46 FPS for the current QQVGA script.
- USB-TTL testing received STM32 USART3 status containing `DX`, `DY`, servo
  pulse widths, and PID parameter fields.

The model's earlier proposal included PC-side AI PID tuning utilities. The
contributor explicitly removed those utilities from submission scope. The
final change therefore contains no API configuration, API key, AI tuning
script, generated Keil artifact, or serial temporary file.

These corrections do not upgrade the results to Zynq PS-PL integration or
whole-system acceptance. They remain STM32/OpenMV prototype observations.

