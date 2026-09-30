# PL spatial majority candidate

Date: 2026-09-30 (China Standard Time). Scope: original RGB565 red-mask
processing in the existing local vendor-camera trial. Vendor source,
bitstreams, license files and camera frames remain outside this public repo.

The previous viewer median suppressed short display jumps, while the raw PL
min/max box remained sensitive to distant isolated red pixels. This candidate
adds a 3×3 binary majority before PL statistics: five matching neighbors are
required. Two 640-bit line memories hold the prior mask rows. Only interior
centers are measured; counts, sums and boxes describe that filtered mask.
The build remains optional (`--spatial-filter`), and header mask version 2
distinguishes it from the original threshold-only version 1.

## Verification observed

- Python: 40 unit tests passed; repository checker passed. These are host
  software checks, not board validation.
- Vivado 2024.2 xsim: `RED_SPATIAL_STATS_TB_PASS`,
  `RED_RESULT_HEADER_TB_PASS` (both header versions) and
  `RED_FRAME_STATS_TB_PASS` (original mode). The spatial bench includes idle
  cycles, repeated frames, reset, speck removal, border coordinates and four
  versus five votes. Changing the private filter threshold from five to six
  caused `five-vote threshold mismatch`, proving that this boundary test
  rejects that specific error.
- Full-frame xsim compared identical raw RGB565 bytes with software. The two
  private camera inputs retained from 2026-09-27 yielded:

| Input SHA-256 | Count | Sum X | Sum Y | Inclusive box |
|---|---:|---:|---:|---|
| `696d2a85a4bf9fca067b0a05581952ca0c6a530a34f9c225284ef98512717a8a` | 20433 | 5653296 | 2242062 | `(215,25,339,193)` |
| `35e7094712e9e7d73c00c823737fbbdbea4349485f78554a9b5ec8d0a0e2813` | 19870 | 5436046 | 2180778 | `(210,25,335,194)` |

All printed fields matched exactly. A full-red 640×480 frame also matched
count 304964, sum X 97435998, sum Y 73038878 and box `(1,1,638,478)`.
These comparisons establish simulation behavior on those bytes; the retained
inputs do not capture the later 300-frame flicker episode.

- Private synthesis, routing and bit generation completed for the existing
  vendor trial target `xc7z100ffg900-2`. Routed constrained-path WNS is
  3.019 ns and WHS 0.085 ns. DRC lists warnings and no errors; the timing
  report still lists 90 non-clocked pins and 227 unconstrained endpoints.
  Full timing closure and physical package/speed identification remain open.
  Total placed resources are 1820 LUTs and 1634 registers; 20 LUTs implement
  distributed RAM. These totals include the vendor transport and camera logic.
- Local bitstream SHA-256:
  `4b42c32436a0b9ac7e089ed15777536709839eab8b58314c8e3b37031ce7e121`.
  This bitstream has **not** been downloaded in this session.
- Wired NIC: `192.168.1.102/24`, 1 Gbps link. A five-second start-command
  probe received zero UDP datagrams. Read-only JTAG discovery found no target.
  Windows reports problem code 10 (`CM_PROB_FAILED_START`) on the FTDI
  USB download device; a targeted device restart was denied by the OS.
  Manual USB reconnection was requested. The route from the bound local
  address to the board was confirmed to use the wired NIC.
  Board power and a working JTAG connection still need confirmation before
  hardware comparison. No Flash or boot media was written.

## Required hardware follow-up

Restore the board/camera/GE/JTAG connection, temporarily load the candidate,
and run 100 same-frame comparisons with `--compare-raw-mask` while the paper
target is still. Then measure a longer receive run and inspect the live
overlay. Record the raw PL box variations independently of the viewer's
seven-result median. Do not claim reduced hardware flicker from this build
or its simulations alone.

Majority can remove thin/small targets, round corners and fill small holes.
It does not separate multiple red regions or reject larger red distractions.
Lighting, border targets and target motion still need physical experiments.
