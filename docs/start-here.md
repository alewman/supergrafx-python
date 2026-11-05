# Start here: the SuperGrafx as an add-on

Read the base board's [docs/sockets.md](../../pcengine-python/docs/sockets.md) ("SuperGrafx: add-on,
with a measured fallback"), its [handoff-brief.md](../../pcengine-python/docs/handoff-brief.md) (M6 row,
U14) and MacDonald's `sgxtech.txt` (`pcengine-python/reference/docs/sgxtech.txt`, tier 2) first.

## The machine

[hw: sgxtech] A PC Engine with 32 KiB of work RAM, a second VDC with its own 64 KiB of VRAM, and a
**HuC6202 VPC** between the two VDC pixel buses (9 bits each: sprite flag, palette, colour) and the
VCE. The VPC also decodes the video chip area, mixes by two window areas and four 4-bit priority
groups, and steers `ST0`-`ST2` to either VDC. A switch on the back selects PC Engine compatibility
(VDC 1 mirrored every 4 bytes through `$FF:0000-03FF`) or native SuperGrafx decode.

Native decode of `$FF:0000-03FF`, a 32-byte block repeated through the 1 KiB:

| Offset | Device |
| --- | --- |
| `$00-$03`, `$04-$07` | VDC 1 (mirror) |
| `$08-$0F` | VPC: `$08`/`$09` priority groups, `$0A-$0D` window widths, `$0E` ST steering, `$0F` unused |
| `$10-$13`, `$14-$17` | VDC 2 (mirror) |
| `$18-$1F` | unused, reads `$FF` |

The bank map is the base board's (work RAM in `$F8-$FB`) with 32 KiB instead of the 8 KiB mirror;
`$80-$F7` and `$FC-$FE` read `$FF`.

## The sockets this board uses

| Base socket (docs/sockets.md) | Use here |
| --- | --- |
| 3 one decode | `VideoPage` claims pages `$1FE0-$1FE3` over the base VDC page |
| 6 interrupts | `Board.lines()` ORs both VDCs' IRQ1 (the base board change, see below) |
| 7 pixel path | `Vpc.mix` is the board's `PixelPath`: one row per VDC in, one row out |
| 8 video timing | both VDCs are hsync'd and vsync'd by the base scheduler |
| 12 instances | the second VDC is a second `pcengine_python.vdc.Vdc`; the machine row sets `vdc_count=2` |
| machine table | `SUPERGRAFX = Machine("SuperGrafx", True, work_ram_bytes=32 KiB, vdc_count=2)` |

**One base-board change was needed** and is documented there as
`pcengine-python/docs/issues/0001-second-vdc-not-run-by-the-board.md` (local commit `5d9dc86`):
`Machine.vdc_count` was a table field nothing read, so the board built one VDC only. It now builds
`Board.vdcs`, steps, syncs and reads the rows of all of them. With `vdc_count=1` nothing moves
(tests, and captured frames hashed before and after).

One thing is **not** a socket: `ST0-ST2` look like plain stores to `$1FE000/2/3` on the
bus. `SuperGrafx._store_immediate` reads the core's public `HuC6280.opcode` (huc6280-python commit
after 34f1570, local until released). **That accessor needs a core release and a repin of
pcengine-python** (this add-on's pin follows the board's): the currently pinned core (a379416)
only has the private `_opcode`, so the add-on falls back to it when `opcode` is absent. To try the
accessor before the repin, run with `PYTHONPATH=/data/emu/huc6280-python/src` (dev-only override;
nothing is installed or repinned). Once the pinned core has `opcode`, drop the fallback.

## Module shape

```
supergrafx_python/
  machine.py   the SUPERGRAFX row of the base board's machine table
  vpc.py       Vpc (registers, mix = PixelPath, named switches) and VideoPage (the decode)
  board.py     SuperGrafx: a base Board with the row, the VPC as pixel path, the page claimed
scripts/
  sgx_ours.py      run a card for N frames, modes sgx | compat | base (the fallback)
  sgx_pictures.py  the five cards against Mesen2 and Beetle PCE (one niced run at a time)
  sgx_mame.py      the five cards against MAME `sgx` (crude statistics)
```

Nothing is copied from the base board; the picture scripts import the base repository's
`scripts/` (tooling) by path (`PCENGINE_PYTHON`, default `/data/emu/pcengine-python`).

## Rules

Python floor 3.11 (PyPy); correct, not fast; HuCards read in place by path, never committed; local git
only; temp files only in a scratch directory; no destructive one-liners.
