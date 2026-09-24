# Third-party sources and licensing

The initial repository contains original project documentation and repository tooling. It does not redistribute vendor FPGA projects, commercial IP, model weights, or externally sourced image datasets.

| Dependency/reference | Version | Use | Licensing handling |
|---|---|---|---|
| `actions/checkout` | v4.2.2, commit `11bd71901bbe5b1630ceea73d27597364c9af683` | CI checkout action, referenced rather than vendored | Upstream MIT; preserve upstream terms when vendoring |
| `obra/superpowers` | Source pages listed in `docs/sources.md` | Planning and verification methods only | No full Skill text copied or scripts executed |
| AMD/PYNQ/Vitis resources | See `docs/sources.md` | Technical references | No code or board image included |
| `Vickyiii/fpgachina26-amd` | `e47e4a81c2a6a35dbd0b25dcaa4d2edef9daf643` | 2026 AMD track and open-topic requirements reference | No `LICENSE` found; cite requirements only, do not copy repository content into this MIT project |

For each future import, record its source URL, pinned commit/tag, files used, license text location, modifications, and redistribution approval. Unknown licensing is a blocker to copying source into this public repository. The root MIT license applies only to material the contributors have authority to license.
