<!-- SPDX-License-Identifier: MIT -->
# Clean rewrite (2026-11-19)

The provenance audit of 2026-11-13 ([provenance.md](provenance.md)) found nothing in this add-on
that follows GPL code, but two facts whose only stated source was GPL source that had been read:
the window origin (U-SGX1) and what shows where both VDC pixels are transparent (U-SGX5). This
pass re-established both from permitted sources and rewrote the code that held them. It is part
of the PC Engine family's clean rewrite and follows the family charter (licences and provenance)
and the sound cores' restart rules (sn76489-python `docs/restart.md`).

## The rules, as applied here

1. **No GPL or LGPL source is read**: Mednafen, Beetle PCE, Mesen2, Geargrafx, the MiSTer core,
   MAME's GPL files. Not to learn, not to check a constant, not when a comparison fails.
2. **The code being replaced is not read.** `Vpc.WINDOW_ORIGIN` with its comment,
   `Vpc.window_edge` and `Vpc._mix_run` were moved aside into the git-ignored `scratch/withdrawn/`
   by a helper that printed only line ranges, and written again from sgxtech, the tests that define
   the interface, and the measurements below.
3. **Permitted sources**: MacDonald's `sgxtech.txt` (hardware-tested research); MAME's
   `huc6202.cpp` (first line `license:BSD-3-Clause`, Wilbert Pol), read; nothing was ported from
   it, so no notice is carried.
4. **GPL emulators are run as closed boxes**: Mesen2 (b9fa69d, the base board's `mesen_run.py`)
   and Beetle PCE (b96c11e, through the base board's libretro host), on probe cards of our own
   (`scripts/sgx_probe.py`). A value fitted to them is marked "closed-box measurement (emulator
   tier)" and is overruled by any document or console result.
5. **Every rule names its source** with the family's evidence tags, or says it is a choice.
6. **The gates are external**: the quick suite, the five library cards at frame 300 against
   Mesen2 and Beetle PCE, Daimakaimura into stage 1 (frames 800, 1000, 1600), and the probes.

## What was replaced

| Item | Before | After |
| --- | --- | --- |
| U-SGX1 window origin | a GPL emulator's constants, read from source | sgxtech for the form (`W - $40`, single pixels); the origin per dot clock a closed-box measurement: both detectors 32 at 5.37 and 10.7 MHz; at 7.16 MHz Beetle PCE 46, Mesen2 24. Default unchanged, `{4: 32, 3: 46, 2: 32}`; 7.16 MHz provisional |
| U-SGX5 both transparent | "two emulators agree", read from source | closed-box measurement on both detectors at every dot clock, both directions (VDC 1 in its border, VDC 2 in its border): VDC 2's value. MAME's BSD source has the same rule. Unchanged; a test added |
| C-SGX1, U-SGX2, U-SGX3 wording | GPL internals named in comments and docs | the closed-box observations only; U-SGX3 is now stated as this model's choice |

No default changed. Downstream (supergrafx-rust) carries no behaviour change; only comments and
documents follow.

## Repin to the clean base board (2026-11-19)

The base board's own clean rewrite (pcengine-python 3318027: a new VDC line machine written from
Hudson's manual, pcetech and MAME's BSD-3 files; core huc6280-python 6ce348e) landed after the
pass above, and this add-on now pins it. Neither commit is on GitHub yet: the pin in
`pyproject.toml` names the full hash on GitHub as usual, and until Aubrey pushes both, the venvs
are installed from the local clones:

```sh
for v in .venv-pypy .venv; do
  $v/bin/python -m pip install --force-reinstall --no-deps \
    "git+file://$PWD/../huc6280-python@6ce348e13c9ef3009bd07e7938c4b48956eeadc6" \
    "git+file://$PWD/../pcengine-python@3318027e5c34f1e211515f95233a0853938a5f53"
done
```

**Interfaces.** Nothing here used what the base board removed (`vertical_at_line_start`,
`latch_byr`, `latch_bxr`, `_step_bg_y`, `line_counter_step`, `commit_unless_dma`,
`force_complete`, `SAT_DOTS`, `DMA_DOTS_PER_WORD`, `CLOCKS_PER_SPRITE`): the add-on reaches the
VDCs only through `Board`, `Machine(vdc_count=2)`, `PixelPath` rows, `VideoTiming` and the VDC's
port, all unchanged. No code adaptation was needed. Save states from the old pin do not load
(the base board's sequencer state changed); the round-trip test passes on the new one.

**The window origin, re-measured.** The base board's display now starts 8 dots earlier in the row.
`Vpc.WINDOW_ORIGIN` is counted in row dots, so it was retaken with `scripts/sgx_probe.py` (not
shifted by assumption). With the old constant on the new base, every detector's window edge sat
8 dots before ours at all three dot clocks, and each detector's alignment offset to our picture
(dx) fell by exactly 8, so the edges kept their place against the picture while the picture
moved in the row:

| Dot clock | Beetle PCE b96c11e | Mesen2 b9fa69d | old constant | new constant (closed-box measurement, emulator tier) |
| --- | --- | --- | --- | --- |
| 5.37 MHz (divider 4) | 24 | 24 | 32 | **24** |
| 7.16 MHz (divider 3) | 38 | 16 | 46 | **38** (Beetle's, provisional: the detectors still differ by 22) |
| 10.7 MHz (divider 2) | 24 | 24 | 32 | **24** |

With the new constant the probes give the same figures as before the repin on every probe and
judge (window edges equal to both detectors at 5.37 and 10.7 MHz and to Beetle PCE at 7.16 MHz;
the `clear-*`, `off-*` and `one-*` probes the same pixel and row fractions as on the old base).
Raw lines: runs `probes-base-3318027-origin-old` and `probes-base-3318027-origin-remeasured` in
[m6-results.jsonl](m6-results.jsonl).

**The judges, before (base 4c32f26) and after (base 3318027).**

| Judge | Before | After |
| --- | --- | --- |
| Quick suite, PyPy and CPython | 44 passed | 44 passed (two window tests take the re-measured origin) |
| Slow suite | none in this repository | none |
| Five cards, frame 300, rows against Mesen2 / Beetle PCE | 1.0000 / 1.0000 on four; Granzort 0.9959 / 1.0000 (C-MESEN1, row 0) | the same |
| Daimakaimura, `run@400+10 run@700+10`, frames 800, 1000, 1600 | 1.0000 / 1.0000 | 1.0000 / 1.0000 |
| Window and backdrop probes (15 probe cards x 3 judges) | as recorded above | the same, after the re-measure |

The frame-300 runs were made with the old origin, the Daimakaimura runs partly with the new one:
no card brings a window edge into view (all windows 0 at frame 300; Daimakaimura's stage 1 holds
window 2 at `$3FF`, past the row at any origin), so the origin cannot change them. The base-mode
fallback and MAME runs (`sgx_fallback.py`, `sgx_mame.py`) were not rerun: the first compares the
board with itself, and MAME draws no window on the probes. Raw lines: run
`base-3318027-2026-11-19`.

**What supergrafx-rust must carry**: `WINDOW_ORIGIN = {4: 24, 3: 38, 2: 24}` (was
`{4: 32, 3: 46, 2: 32}`), together with the base board's own changes (pcengine-python
`docs/restart.md`, "What the Rust transcription must carry", through the pcengine-rust pin).
Nothing else in this add-on's behaviour changed.
