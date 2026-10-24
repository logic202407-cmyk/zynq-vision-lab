# Standalone STM32 fixed-camera paper bench

Date: 2026-10-24, Asia/Shanghai. Base: main commit
`0daf92f09ed912635169087b07914b65775ab7ff`.

## Scope and output

The user narrowed this change to the STM32 side. The intended later scene uses
separate white paper sheets, processed left to right, with a fixed camera and an
independently moving gimbal. This change does not implement detection, ranking,
camera-to-PWM calibration, PS frame capture, or Zynq UART pin assignment.

`src/prototype/fixed_camera_stm32/` provides an independently buildable
STM32F103C8 application. It accepts calibrated absolute PWM through USART3,
moves dark on `center`, and only illuminates after a separate `point` command.
The caller must wait for completion and verify status before continuing. The
interface documentation distinguishes commanded PWM from measured position.

Seven inherited module files remain unchanged from the working local drawing
application. The packaged trajectory implementation additionally fixes line
range validation. A small new entry point initializes illumination off without
starting PWM; the exception handlers force PA4 low before halting.

No original local bench project was edited for this publication. No firmware
binary, ST vendor source, compiler, license file, private image or hardware log
has been added to Git.

## Actual ARM build

Command, from repository root:

```text
python src/prototype/fixed_camera_stm32/build.py --keil-root C:/Keil_v5
```

Tools: ARM Compiler 5.06 update 5 build 528, external Keil STM32F1xx DFP 2.2.0
and ARM CMSIS 5.0.1. Compilation, assembly, linking and Intel HEX export
succeeded without error or warning diagnostics.

Final code: 13500 bytes; RO data: 608; RW data: 48; ZI data: 1704.
ROM total: 14156 bytes; RW + ZI: 1752 bytes. The link regions are 64 KiB Flash
and 20 KiB RAM. Static maximum stack is 416 bytes plus unknown startup-function
stack information; the external startup allocates 1024 bytes of stack.

Build outputs, commands, source SHA-256 hashes and logs remain in the local
system-temporary `fixed-camera-stm32-build` directory, outside the repository.
The script does not invoke a programmer or open a serial port.

## Actual host checks

```text
python -B -m unittest discover -s tests -p "test_fixed_camera*.py" -v
```

Result: **44 tests passed**, no skips. They compile real packaged C code with
host GCC, rather than reimplementing the trajectory in Python:

- 30 core checks cover trajectory geometry, parsing, travel limits, timing,
  stop, wraparound, circle/square/line behavior and backlash compensation.
- 13 console checks run the actual console loop against fake UART registers,
  clock, PWM and illumination outputs. They cover startup, two sequential
  positions/points, busy rejection, partial/overlong/corrupt input, UART error,
  stop, and sender silence during a point.
- One build-failure regression verifies that a missing toolchain cannot leave
  the previous successful ELF, HEX and manifest behind.

Review found and corrected two inherited line-validator omissions: negative
direction compensation and an interior pitch maximum/minimum. Regression
vectors reproduce both failures; 400 deterministic candidate strokes also
check accepted paths against pulse limits throughout the segment.

The fake peripherals do not verify electrical UART behavior or real-time
scheduling. Host compilation of the core is not an ARM execution test.

Final repository-wide checks also ran:

```text
python -B tools/check_repository.py
python -B -m unittest discover -s tests -q
git diff --check
```

Result: repository checks passed; **84 tests passed**, no skips; no whitespace
errors. This includes the 44 STM32 checks above and 40 pre-existing tests.

## Evidence boundary

This standalone application has **not been flashed or board-tested** in this
task. There was no Zynq-to-STM32 communication or multiple-paper hit test. Older
physical drawing observations belong to the original application and do not
promote this entry to board-verified status.

ASCII has no CRC, command identity or session protection. A single caller must
serialize commands and must not automatically replay `point`. Disconnection
does not abort an accepted task; under normal scheduling the point closes after
its 300 ms illumination phase. The loop-gap check depends on the loop resuming.
Actual positioning, deadband, alignment and spot containment require later
physical verification. FPGA evidence statuses retain their previous values.
