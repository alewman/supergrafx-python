# Milestone 6 record: the SuperGrafx

Date 2026-11-05. Pins: `pcengine-python` 009d1ee (807a366 + issue 0001 as 5d9dc86 + the M6 status docs), which brings
`huc6280-python` a379416. Local repository, nothing pushed. Tiers as in the base board's
[validation.md](../../pcengine-python/docs/validation.md): 1 hardware-captured, 2 hardware-verified
research (MacDonald's `sgxtech.txt`), 3 manufacturer, 4 research, 5 emulator-derived (detectors).

## Exit (handoff-brief M6)

> the 5 library cards; the VPC priority/window behaviours of sgxtech reproduced

- **The 5 cards** boot to a picture on this board and agree with the detectors: at frame 300 four are
  **row-identical** with both Mesen2 and Beetle PCE (4 x 242 of 242 rows, every pixel), the fifth is
  identical with Beetle and differs from Mesen2 in **one row, frame line 14**, a Mesen2 behaviour
  that is not the VPC's (below). MAME `sgx` agrees on colour mix and row content for four, and
  differs on the fifth (named below). Table in "Pictures".
- **The sgxtech behaviours** (registers, power-up values, the four window areas and their nibbles,
  window width edge cases, both priority codes, enables, both layers off, ST steering, VDC 2's
  interrupt, the compatibility decode, the bank map) are reproduced by 36 directed tests
  (`tests/`, CPython and PyPy; a 37th is the gate: with VDC 2 idle the add-on draws exactly what the
  base mode draws on Covell's CPU test), including a test through the real HuC6280 core that `ST0-ST2` follow
  `$0E` and plain stores do not. Three behaviours rest on the detectors and one game, not on sgxtech;
  they are the C/U entries below.

## What was built

[start-here.md](start-here.md) has the machine and the sockets. In short: `Vpc` (registers + the mix,
the board's `PixelPath`), `VideoPage` (the `$FF:0000-03FF` decode with the compatibility switch),
`SuperGrafx` (a base `Board` with `SUPERGRAFX` = 32 KiB RAM + `vdc_count=2`, the VPC as pixel path,
the page claimed). Nothing is copied from the base board.

**One base-board change** ([pcengine-python/docs/issues/0001](../../pcengine-python/docs/issues/0001-second-vdc-not-run-by-the-board.md),
commit 5d9dc86): the board now builds one `Vdc` per `Machine.vdc_count` and steps, syncs, reads and
ORs IRQ1 over all of them. `vdc_count=1` is unchanged: the base tests pass on CPython and PyPy (230),
and captured frames (SHA-256 of rows and dividers, 150 frames) of Alien Crush (USA) and Covell's CPU
test are identical before and after. The base board's 18-picture gate was **not** rerun: no VDC or
VCE code changed, and the day's constraint was no sweeps.

Not built, by scope: the S-EXP port (sgxtech: NEC released one peripheral and no software is known
to use it; socket 11 is the place), CD on the SuperGrafx (via the EXT BUS; the base's M7), work-RAM
power-up contents.

## Pictures (the five library cards)

Cards are read in place from `/data/emu/roms-retrobat/supergrafx/`. Frame 300, `scripts/sgx_pictures.py`
(ours under PyPy; Mesen2 sprites on and Beetle PCE over frames 297-303, the best frame and the
dx the base board's M5 comparison finds; equal at the 9-bit palette value):

| Card | VPC at frame 300 | Mesen2 rows / px | Beetle rows / px | MAME `sgx` (tv / rows) |
| --- | --- | --- | --- | --- |
| 1941 Counter Attack | `$77 $77` | 1.0000 / 1.0000 (frame 300) | 1.0000 / 1.0000 | 0.031 / 1.00 |
| Aldynes | `$33 $33` | 1.0000 / 1.0000 (297) | 1.0000 / 1.0000 | 0.000 / 1.00 |
| Battle Ace | `$00 $30` | 1.0000 / 1.0000 (297) | 1.0000 / 1.0000 | 0.032 / 0.91 |
| Daimakaimura | `$77 $77` | 1.0000 / 1.0000 (299) | 1.0000 / 1.0000 | 0.051 / 1.00 |
| Madou King Granzort | `$00 $30` | 0.9959 / 0.9965 (300) | 1.0000 / 1.0000 | 0.164 / 0.60 |

(VPC windows were 0 on all five at frame 300; the window and mixing code is judged by the directed
tests and the 600-frame row below.)

Triage of what is not identical:

- **Granzort, Mesen2, row 0.** Only the first picture row (frame line 14) differs: ours and Beetle
  draw the card's first display line, Mesen2 draws it blank. **Not the VPC**: the same card renamed
  `.pce` (Mesen2 then runs it with one VDC) also gives a blank row 0. A Mesen2 line-14 behaviour for
  a card whose display starts on line 14; Beetle agrees with this board. Cause named, not a board
  defect.
- **Granzort, MAME.** tv 0.164 / rows 0.60 against 0.0-0.05 / 0.9-1.0 for the rest. MAME is
  sampled at 5 s of its own clock, not at frame 300 (base validation.md: "whether the games are at
  different moments after power-on ... was not established"); Mesen2 and Beetle at frame 300 are
  the judges, MAME is a crude detector here. Not triaged further.
- **Battle Ace, MAME rows 0.91**: the same kind of difference, smaller.

### Second checkpoint, frame 600

Same script, `--target 600` (references 597-603):

| Card | Mesen2 rows / px | Beetle rows / px | VPC writes in 600 frames |
| --- | --- | --- | --- |
| 1941 Counter Attack | 1.0000 / 1.0000 | 1.0000 / 1.0000 | one init set; `$0E` once; VDC 2 holds 25,202 words |
| Aldynes | 1.0000 / 1.0000 | 1.0000 / 1.0000 | one init set; VDC 2 untouched (0 words) |
| Battle Ace | 1.0000 / 1.0000 | 1.0000 / 1.0000 | one init set; VDC 2 holds 11,026 words |
| Daimakaimura | 1.0000 / 1.0000 | 1.0000 / 1.0000 | windows `$0A-$0D` written 602 times each (every frame), `$0E` 917 times (ST steering switched through the frame) |
| Madou King Granzort | 0.9959 / 0.9965 | 1.0000 / 1.0000 | two priority sets, `$0E` and `$0F` once; same row 0 as above |

Daimakaimura exercises the window registers and the ST steering every frame and stays row-identical to
both detectors; no card holds a non-zero window at the end of a frame at either checkpoint, and none
was driven into gameplay (no input is given), so **window edges against a game are not judged by a
picture**: the directed tests, and the two detectors' source (U-SGX1), are what judge them.

## The base-mode fallback, measured

The fallback is the SuperGrafx **as a mode of the plain board**: `Machine(work_ram_bytes=32 KiB,
vdc_count=1)`, one VDC, no VPC, no second VDC (`sgx_ours.py --mode base`), i.e. what folding the
SuperGrafx into the base machine table would draw if the games' VDC 2 layers were simply dropped.
Same card, same frame 300, the two pictures compared at the 9-bit value
(`scripts/sgx_fallback.py`):

| Card | equal pixels | equal rows | first difference (row, col: add-on, base) |
| --- | --- | --- | --- |
| 1941 Counter Attack | 0.868 | 0.207 | 12, 59: `120` vs `0` |
| Aldynes | 1.000 | 1.000 | none (VDC 2 shows nothing yet) |
| Battle Ace | 0.916 | 0.802 | 99, 88: `438` vs `0` |
| Daimakaimura | 0.806 | 0.512 | 27, 93: `3` vs `0` |
| Madou King Granzort | 0.342 | 0.000 | 0, 32: `292` vs `0` |

Four of five cards are visibly wrong without VDC 2 and the VPC (the add-on is the detectors'
picture, rows identical). **The fallback is not a substitute**; it is a correct *PC Engine* mode
for the day a SuperGrafx card is wanted as a one-VDC picture, nothing more. The reason to prefer
the add-on stands on measurement, and the reason to fold it in (the pixel-path socket on the hot
path) was already refuted in the base board's M3: `PixelPath` costs within noise
([m3-record.md](../../pcengine-python/docs/m3-record.md), "PixelPath on the per-line path").

Speed (wall clock, 300 frames, PyPy 7.3.20, niced on a machine at load 25-40, so only the ratio
is of interest and even that is noisy): add-on 133-432 s against base mode 75-228 s per card, about
1.5-2x. Two VDCs and a per-line mix cost that much; **correct, not fast** (reference-board rule),
a -fast fork's job.

## Entries (U unknown, C conflict), each with its tier and the switch that holds it

Provisional defaults are **named class attributes** (`Vpc`, `VideoPage`), so a judge changes one
line. None is decidable without a console.

| # | Entry | Sources | Tier | Default (attribute) |
| --- | --- | --- | --- | --- |
| **C-SGX1** | Which 2-bit priority code is which. sgxtech: `01b` = VDC 1 sprites behind the VDC 2 background, `10b` = VDC 2 sprites in front of the VDC 1 background. Mednafen and Mesen2 read the register the other way round, and Mednafen's source says Dai Makai Mura uses code `01b` *expecting* VDC 2 sprites in front of VDC 1's background | sgxtech (2) against two detectors and a game's behaviour (5). Daimakaimura is row-identical to both detectors with the VPC at `$77` (code `01b`) | 2 vs 5 | `Vpc.PRIORITY_LABELS = "detectors"`; `"sgxtech"` swaps the two codes; directed tests for both |
| **U-SGX1** | Where a window's edge falls: row dot `W - 0x40 + origin(dot clock)`. sgxtech gives only "starts at the leftmost physical pixel; `$0040` is zero width" | Mednafen: origin 32 (5.37 MHz), 46 (7.16), 32 (10.7); Mesen2: 48 at every clock (a 16-dot disagreement at 5.37 MHz). No card here moves a window by frame 300 | 5 | `Vpc.WINDOW_ORIGIN = {4: 32, 3: 46, 2: 32}` |
| **U-SGX2** | A window of `W <= 0x40` is disabled (also over the left overscan). Mednafen's counter keeps the left overscan in "both windows" even at `W = 0`; Mesen2 covers `W - 16` dots | sgxtech "values smaller than `$0040` disable the window; I haven't checked the overscan" | 2 (text), overscan unchecked | `Vpc.WINDOW_OFF_AT_OR_BELOW = 0x40` |
| **U-SGX3** | At which dot a VPC register write takes effect mid-line | this model: the first dot whose time is at or after the write (the VCE palette's rule); Mesen2 draws the line up to the write first, Mednafen syncs at the write: same effect to the dot; none of the five cards writes mid-line near frame 300 | 5 | the rule in `Vpc.mix` |
| **U-SGX4** | Whether `ST0-ST2` still follow `$0E` bit 0 with the switch in PC Engine position (`$0E` cannot be written there; only a bit left from native mode) | nothing documents it | none | `VideoPage.ST_STEERS_IN_COMPAT = False` |
| **U-SGX5** | Both VDC pixels transparent in the enabled mix: the result is VDC 2's pixel (its `$000`/`$100` backdrop code) | Mednafen and Mesen2 agree; sgxtech silent | 5 | in `Vpc._mix_run` |
| **U-SGX6** | The VPC and VDC 2 accesses cost the same one extra CPU cycle as a VDC access (the base rule for `$FF:0000-07FF`) | MacDonald's "VDC or VCE access takes one more cycle" (pcetech, tier 2) covers the original chips only | 2 (extrapolated) | the base board's `_finish_access` |
| **U-SGX7** | Work RAM power-up: banks `$F8`/`$FA` mostly zero, `$F9`/`$FB` mostly `$FF`, with some random bytes | sgxtech "Miscellaneous" | 2 | not modelled: zeros (the base U7 default) |
| **U-SGX8** | S-EXP port (74HC157 mux, output bits 2-7), HuC6280A vs HuC6280 (U6) | sgxtech; no known software | 2 | not built; socket 11 |
| **C-MESEN1** | Mesen2 draws frame line 14 blank for Madou King Granzort in SuperGrafx **and** PC Engine mode; Beetle and this board draw it | detectors disagree | 5 | none; named in the table |

## Reproducing

```sh
.venv-pypy/bin/python -m pytest -q            # 36 tests, CPython too (.venv)
python3 -I scripts/sgx_pictures.py /data/emu/roms-retrobat/supergrafx SCRATCH out.jsonl --only Granzort
python3 -I scripts/sgx_fallback.py /data/emu/roms-retrobat/supergrafx SCRATCH out.jsonl
python3 -I scripts/sgx_mame.py     /data/emu/roms-retrobat/supergrafx SCRATCH out.jsonl
```

Every run is one process at a time under `nice -n 10`. Raw result lines of this record:
[m6-results.jsonl](m6-results.jsonl).
