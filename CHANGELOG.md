<!-- SPDX-License-Identifier: MIT -->
# Changelog

Releases are git tags. Not on PyPI (the base board is pinned by git commit).

## Unreleased

- Base board pcengine-python **03ac699** (local): a display that starts before the row is
  cropped and the row keeps its length (found by supergrafx-rust's probe card in compat and base
  mode). Quick suite, the probes and the five cards unchanged (docs/restart.md, last section).

Repin to the base board's clean rewrite (docs/restart.md, "Repin to the clean base board"):

- Base board pcengine-python **3318027** (its clean VDC rewrite; core huc6280-python 6ce348e),
  not yet on GitHub: the venvs install it from the local clones (pin comment). Save states from
  the old pin do not load. No code used the removed base interfaces; nothing to adapt.
- **U-SGX1 re-measured**: the base board's display starts 8 dots earlier in the row, and the
  probes put both detectors' window edges 8 dots earlier in row dots: `Vpc.WINDOW_ORIGIN` is now
  `{4: 24, 3: 38, 2: 24}` (was `{4: 32, 3: 46, 2: 32}`); 7.16 MHz stays Beetle PCE's value,
  provisional (Mesen2 16).
- Judges unchanged: 44 tests; the five cards and Daimakaimura's three later frames give the same
  rows against Mesen2 and Beetle PCE; the probes give the same figures after the re-measure.
- Scripts and a test default the base board's checkout to the sibling `../pcengine-python`
  (no machine path); the documents name the card set as `$NO_INTRO_DIR/...`; SPDX headers on
  every file.

Clean rewrite of the items the 2026-11-13 provenance audit marked unclear (docs/restart.md,
docs/provenance.md). **No default and no behaviour changed.**

- U-SGX1, the window origin: `Vpc.WINDOW_ORIGIN`, its comment and `Vpc.window_edge` withdrawn
  unread and rewritten. The form `W - $40 + origin` from sgxtech; the origin per dot clock is now a
  closed-box measurement on our own probe cards (`scripts/sgx_probe.py`): Mesen2 and Beetle PCE
  both 32 at 5.37 and 10.7 MHz; at 7.16 MHz Beetle PCE 46 (the default, kept, provisional) and
  Mesen2 24. The GPL expression formerly quoted is gone from code and documents.
- U-SGX5, both VDC pixels transparent show VDC 2's pixel: `Vpc._mix_run` withdrawn unread and
  rewritten from sgxtech and the tests; the rule measured closed-box on both detectors at all three
  dot clocks, in both directions; MAME's BSD-licensed `huc6202.cpp` has the same rule. New test
  `test_both_transparent_shows_vdc2s_pixel`.
- U-SGX2 probed (widths `$40`, `$20`, `$41`): the active display agrees with both detectors; in the
  left overscan Mesen2 at 5.37 MHz differs (recorded). New entry C-BEETLE1 (Beetle PCE's overscan
  with only VDC 1 enabled). U-SGX3 is stated as this model's choice.
- Comments and documents no longer name GPL emulators' internals (C-SGX1, U-SGX3, m6-record,
  a pin comment); SPDX headers on the files touched.

## 0.1.1 (2026-11-14)

- Base board: pcengine-python 0.2.0 (core huc6280-python 0.4.0; the board's issue 0004). No change
  in this add-on's own code.

## 0.1.0 (2026-11-12)

The first release: the NEC SuperGrafx as an add-on to pcengine-python.

- The HuC6202 VPC (windows, priority, `ST0-ST2` steering, the video-area decode with the
  compatibility switch), a second VDC and 32 KiB of work RAM, through the base board's sockets.
- The five library cards row-identical to Beetle PCE and, but for one row of Madou King Granzort,
  to Mesen2; the base-mode fallback measured (docs/m6-record.md).
- C-SGX1 decided: the priority codes are read as Mesen2 and Beetle PCE draw them, run as closed
  boxes (`PRIORITY_LABELS = "detectors"`), after Daimakaimura's cutscene and first stage were
  compared under both readings.
- Save states through the base board's `pcengine_python.state`; scripted pad input (`--press`).
- Base board: pcengine-python 0.1.0.
