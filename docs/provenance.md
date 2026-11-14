# Provenance

## Licence provenance (audit 2026-11-13)

Judged against the family charter ("Licences and provenance", rule 3: nothing copied or transcribed
from GPL/LGPL code; GPL programs are run as closed boxes, their source not opened while writing).
Audited from this repository's records only; no GPL source was opened. The rule, the reference trees
and the check are described in pcengine-python's `docs/provenance.md` (same date), whose
`provenance_check.py` re-run against the permissive trees (MAME's PC Engine files, all BSD-3; ares,
ISC; Shadoff's MIT repositories) found nothing in this repository.

| Code | Behaviour source (licence) | Verdict |
| --- | --- | --- |
| `vpc.py`: registers, power-up values, ST steering, the mix | MacDonald's `sgxtech.txt` (research text, facts) | **clean** |
| `vpc.py` `PRIORITY_LABELS = "detectors"` (C-SGX1) | sgxtech against Mednafen/Mesen2's reading; settled by closed-box picture runs (Dai Makai Mura row-identical to Mesen2 and Beetle PCE under this setting) and the game's behaviour | **clean** (fact, closed-box confirmed) |
| `vpc.py` `WINDOW_ORIGIN = {4: 32, 3: 46, 2: 32}` (U-SGX1) | "Mednafen's calibrated `8 + 24`/`8 + 38`" read from its source (GPL-2.0+); no card here moves a window, so no picture confirms it | **unclear**: re-establish by a closed-box run of a window-moving test against Beetle PCE/Mesen2, or from MAME `huc6202.cpp` (BSD-3); drop the quoted expression |
| `vpc.py` U-SGX5 (both pixels transparent: VDC 2's backdrop) | "Mednafen and Mesen2 agree" (read from source) | **unclear** (one behaviour; closed-box checkable) |
| `board.py`, `machine.py` | wiring onto pcengine-python's sockets; sgxtech (32 KiB RAM) | **clean** |
| `scripts/` (sgx_mame, sgx_pictures, sgx_fallback, ...) | run MAME, Mesen2 and Beetle PCE as closed boxes | **clean** |
| `tests/`, `docs/m6-results.jsonl` | our own tests and closed-box results | **clean** |
| `docs/m6-record.md` | cites Mednafen's and Mesen2's behaviour and a comment of Mednafen's in words | **clean** (citations; no code) |

Counts: clean 6, cite 0, rewrite 0, unclear 2.

Inherited: this board runs on pcengine-python, whose VDC line machine (`vdc/sequencer.py` and
parts of `vdc/chip.py`) is marked **rewrite** there; both VDCs here are that code.

History: 13 commits, no deleted files, no C/C++ code in any added line.
