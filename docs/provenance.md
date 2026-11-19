<!-- SPDX-License-Identifier: MIT -->
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
| `vpc.py` `PRIORITY_LABELS = "detectors"` (C-SGX1) | sgxtech against the two detectors' pictures; settled by closed-box picture runs (Dai Makai Mura row-identical to Mesen2 and Beetle PCE under this setting) and the game's behaviour. 2026-11-19: the comment's report of a GPL emulator's source comment removed | **clean** (fact, closed-box confirmed) |
| `vpc.py` `WINDOW_ORIGIN = {4: 32, 3: 46, 2: 32}` (U-SGX1) | 2026-11-19: constant, comment and `window_edge` withdrawn unread and rewritten (docs/restart.md). Form `W - $40 + origin`: sgxtech "Windows" (DOC). Origin: closed-box measurement (emulator tier, Beetle PCE b96c11e, Mesen2 b9fa69d; `scripts/sgx_probe.py`): both 32 at 5.37 and 10.7 MHz; 7.16 MHz Beetle 46, Mesen2 24 (default 46, provisional). MAME 0.285 `sgx` draws no window on the probe. The quoted expression is gone | **clean** (closed-box measurement; 7.16 MHz split) |
| `vpc.py` U-SGX5 (both pixels transparent: VDC 2's backdrop), `_mix_run` | 2026-11-19: `_mix_run` withdrawn unread and rewritten from sgxtech's priority text and the tests. U-SGX5: closed-box measurement (Mesen2 b9fa69d and Beetle PCE b96c11e, `clear-*` probes, three dot clocks, both directions, pixel-identical to ours); MAME `huc6202.cpp` (BSD-3-Clause, read, nothing ported) has the same rule; test added | **clean** (closed-box measurement) |
| `vpc.py` U-SGX3 comment | named two GPL emulators' drawing internals; 2026-11-19 restated as this model's choice | **clean** |
| `board.py`, `machine.py` | wiring onto pcengine-python's sockets; sgxtech (32 KiB RAM) | **clean** |
| `scripts/` (sgx_mame, sgx_pictures, sgx_fallback, ...) | run MAME, Mesen2 and Beetle PCE as closed boxes | **clean** |
| `tests/`, `docs/m6-results.jsonl` | our own tests and closed-box results | **clean** |
| `docs/m6-record.md` | cited Mednafen's and Mesen2's behaviour read from source and a comment of Mednafen's in words; 2026-11-19 rewritten to closed-box observations (C-SGX1, U-SGX1-3, U-SGX5, the new C-BEETLE1) | **clean** |
| `scripts/sgx_probe.py` (2026-11-19) | our own probe cards; runs Mesen2 and Beetle PCE as closed boxes through the base board's runners | **clean** |
| `pyproject.toml`, `CHANGELOG.md` | a pin comment and the 0.1.0 entry named a GPL emulator's formulas/reading; reworded 2026-11-19 | **clean** |

Counts (2026-11-19): clean 11, cite 0, rewrite 0, unclear 0. Before: clean 6, unclear 2.

Inherited: this board runs on pcengine-python, whose VDC line machine (`vdc/sequencer.py` and
parts of `vdc/chip.py`) is marked **rewrite** there; both VDCs here are that code.

History: 13 commits, no deleted files, no C/C++ code in any added line.

### Clean rewrite, 2026-11-19

The two unclear items were settled without reading any GPL source or the withdrawn code
([restart.md](restart.md)). Sources used: MacDonald's `sgxtech.txt` (DOC, hardware-tested
research); MAME `src/devices/video/huc6202.cpp` (BSD-3-Clause, copyright-holders Wilbert Pol: read
as a third opinion, nothing ported, so no notice is carried); Mesen2 b9fa69d and Beetle PCE
b96c11e run as closed boxes on our own probe cards. The inherited VDC (`pcengine-python`'s
`vdc/sequencer.py`, `vdc/chip.py`) is being rewritten in the base repository at the same time;
this add-on's pin (4c32f26) did not move, and its picture results are to be re-run once the base
board's rewrite lands.
