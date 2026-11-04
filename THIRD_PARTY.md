# Third-party sources and licensing

The repository contains original RTL, host tools, interface firmware, project documentation and verification records. It does not redistribute vendor FPGA projects, commercial IP, model weights, or externally sourced image datasets.

| Dependency/reference | Version | Use | Licensing handling |
|---|---|---|---|
| `actions/checkout` | v4.2.2, commit `11bd71901bbe5b1630ceea73d27597364c9af683` | CI checkout action, referenced rather than vendored | Upstream MIT; preserve upstream terms when vendoring |
| `obra/superpowers` | Source pages listed in `docs/sources.md` | Planning and verification methods only | No full Skill text copied or scripts executed |
| AMD/PYNQ/Vitis resources | See `docs/sources.md` | Technical references | No code or board image included |
| `Vickyiii/fpgachina26-amd` | `e47e4a81c2a6a35dbd0b25dcaa4d2edef9daf643` | 2026 AMD track and open-topic requirements reference | No `LICENSE` found; cite requirements only, do not copy repository content into this MIT project |

For each future import, record its source URL, pinned commit/tag, files used, license text location, modifications, and redistribution approval. Unknown licensing is a blocker to copying source into this public repository. The root MIT license applies only to material the contributors have authority to license.

## Skystar STM32F407 references (2026-10-27)

`board/skystar_f407/` contains original connection tables and redrawn functional wiring diagrams. Vendor schematics, board photos, SDK sources and firmware binaries are not included in this documentation submission. Official acquisition links and SHA-256 fingerprints of the locally consulted PDFs are recorded in `board/skystar_f407/sources.md` and `sources.json`. Online vendor packages can change; the recorded fingerprints identify the reviewed local versions. The root MIT license does not relicense external vendor documents.

## Team-supplied media and submission documents

`assets/system_front.jpg` and the hardware images embedded in the design report were supplied by the project team. Copyright is retained by their owners; these media are supplied for project review and presentation, not relicensed as MIT software. The report and poster contain cited external references; their third-party rights remain unchanged. Vendor source projects and tool license files are not included in this final source package.
