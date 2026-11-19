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
