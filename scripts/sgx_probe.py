#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Window and backdrop probes: tiny SuperGrafx HuCards of our own, run on this board and on Mesen2
and Beetle PCE as closed boxes, and the pictures measured (U-SGX1, U-SGX5).

    python3 -I scripts/sgx_probe.py SCRATCH RESULTS.jsonl [--frames 60] [--only NAME]

Needs numpy and Pillow (the system python3); the board runs under `.venv-pypy`. The detectors are
driven by the base board's runners (`m2_refs.run_one`, tooling, imported by path from
`$PCENGINE_PYTHON`, default /data/emu/pcengine-python), one after the other under `nice`. The
images are written into SCRATCH as `.sgx` files (the detectors pick the SuperGrafx by that
extension) and are not committed. One JSON line per probe and judge goes to RESULTS.

Every image is this repository's own: a few hundred bytes of HuC6280 code assembled below and
data from formulas. The VCE colour table holds entry *i* = colour word *i* for all 512 entries,
so a pixel's 9-bit colour in any picture is the palette entry that produced it.

**Window probes** (`win-<clock>-<n>`). Both VDCs show the same opaque texture across their whole
display, VDC 1 in background palettes 0-7 and VDC 2 in palettes 8-15, so every pixel says which
VDC it came from. The VPC is set to show VDC 2 where both windows cover, VDC 1 where only
window 2 does, and VDC 2 where neither does ($08 = $12, $09 = $21); window 1 is the shorter.
Each row of the active display then reads VDC 2 | VDC 1 | VDC 2, and the two switches are the two
window edges. They are reported in this board's row dots, through each detector's alignment to
our own picture (the texture fixes it), so they compare directly with `Vpc.window_edge`. One
probe per dot clock and window pair.

**Backdrop probe** (`clear-<clock>`, U-SGX5). Both VDCs show only transparent tiles; VDC 1's
display is 32 dots narrower than VDC 2's (16 a side) and VDC 2's is 32 lines shorter, and every
area takes both VDCs in the default order ($08 = $09 = $33). Where VDC 1 is in its border
(code $100) over VDC 2's transparent display (colour 0 of a background palette) and the other
way round, the picture shows whose transparent value wins: entry $100 or entry $000.
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import subprocess
import sys
import time
from itertools import pairwise
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPY = ROOT / ".venv-pypy/bin/python"
ORG = 0xE000
VDC1, VDC2 = 0x0000, 0x0010

# Display timing per VCE dot clock: VCE control value, HSR, HDR (common game settings; 256, 352
# and 512 dots wide).
CLOCKS = {
    "5": (0x00, 0x0202, 0x041F),
    "7": (0x01, 0x0303, 0x062B),
    "10": (0x02, 0x0502, 0x0C3F),
}
# Window register pairs (window 1, window 2) per clock: two pairs, the second a few dots on, so
# one-dot steps show (sgxtech: "the windows can have their width defined in units of single pixels").
WINDOWS = {
    "5": ((0x090, 0x104), (0x091, 0x109)),
    "7": ((0x0AE, 0x13A), (0x0AF, 0x13F)),
    "10": ((0x0E0, 0x1A8), (0x0E1, 0x1AD)),
}


class Asm:
    def __init__(self) -> None:
        self.code = bytearray()

    @property
    def here(self) -> int:
        return ORG + len(self.code)

    def b(self, *values: int) -> None:
        self.code.extend(values)

    def data(self, blob: bytes) -> int:
        at = self.here
        self.code.extend(blob)
        return at

    def store(self, address: int, value: int) -> None:
        if value:
            self.b(0xA9, value, 0x8D, address & 0xFF, address >> 8)  # LDA #, STA abs
        else:
            self.b(0x9C, address & 0xFF, address >> 8)  # STZ abs

    def tia(self, source: int, destination: int, length: int) -> None:
        self.b(0xE3, source & 0xFF, source >> 8, destination & 0xFF, destination >> 8,
               length & 0xFF, length >> 8)  # fmt: skip

    def reg(self, base: int, register: int, value: int) -> None:
        """A VDC register through plain stores (not ST0-ST2)."""
        self.store(base + 0, register)
        self.store(base + 2, value & 0xFF)
        self.store(base + 3, value >> 8)


def words(values) -> bytes:
    return b"".join(bytes((v & 0xFF, (v >> 8) & 0xFF)) for v in values)


def tiles(opaque: bool) -> bytes:
    """16 tiles of 8x8; opaque ones have no colour-0 pixel, a different pattern each."""
    out = bytearray()
    for t in range(16):
        lo, hi = [], []
        for y in range(8):
            planes = [0, 0, 0, 0]
            for x in range(8):
                c = 1 + (x * 5 + t * 3 + y * 7) % 15 if opaque else 0
                for p in range(4):
                    if c >> p & 1:
                        planes[p] |= 0x80 >> x
            lo.append(planes[0] | planes[1] << 8)
            hi.append(planes[2] | planes[3] << 8)
        out += words(lo + hi)
    return bytes(out)


def bat(palette_base: int) -> bytes:
    """A 32x32 BAT over the tiles at VRAM $1000 (tile number $100 on), palettes varying."""
    cells = []
    for row in range(32):
        for col in range(32):
            tile = (col * 7 + row * 3) % 16
            palette = palette_base + (col * 3 + row) % 8
            cells.append(palette << 12 | (0x100 + tile))
    return words(cells)


def build(clock: str, window: tuple[int, ...] | None) -> bytes:
    vce, hsr, hdr = CLOCKS[clock]
    a = Asm()
    palette = a.data(words(range(512)))  # entry i holds colour word i
    pattern = a.data(tiles(window is not None))
    bat1 = a.data(bat(0))
    bat2 = a.data(bat(8))
    reset = a.here
    a.b(0x78, 0xD4, 0xD8)  # SEI, CSH, CLD
    a.b(0xA9, 0xFF, 0x53, 0x01)  # LDA #$FF, TAM #$01: the hardware page at $0000
    a.b(0xA9, 0xF8, 0x53, 0x02)  # LDA #$F8, TAM #$02: work RAM at $2000
    a.b(0xA2, 0xFF, 0x9A)  # LDX #$FF, TXS
    a.store(0x1402, 0x07)  # IRQ2, IRQ1 and the timer masked
    a.store(0x0400, vce)
    a.store(0x0402, 0)
    a.store(0x0403, 0)
    a.tia(palette, 0x0404, 1024)
    hsw, hds = hsr & 0x1F, hsr >> 8
    hdw, hde = hdr & 0x7F, hdr >> 8
    for base, table in ((VDC1, bat1), (VDC2, bat2)):
        h_sr, h_dr, vdw = hsr, hdr, 0x00DF
        if window is None and base == VDC1:  # 32 dots narrower, centred
            h_sr = (hds + 2) << 8 | hsw
            h_dr = (hde + 2) << 8 | (hdw - 4)
        if window is None and base == VDC2:  # 32 lines shorter
            vdw = 0x00DF - 32
        for address, blob, length in ((0x0000, table, 2048), (0x1000, pattern, 512)):
            a.reg(base, 0x00, address)  # MAWR
            a.store(base + 0, 0x02)  # VWR
            a.tia(blob, base + 2, length)
        a.reg(base, 0x0A, h_sr)
        a.reg(base, 0x0B, h_dr)
        a.reg(base, 0x0C, 0x1702)  # VPR
        a.reg(base, 0x0D, vdw)  # VDW
        a.reg(base, 0x0E, 0x000C)  # VCR
        a.reg(base, 0x09, 0x0000)  # MWR: 32x32 BAT
        a.reg(base, 0x07, 0x0000)  # BXR
        a.reg(base, 0x08, 0x0000)  # BYR
        a.reg(base, 0x05, 0x0080)  # CR: background only, no interrupts
    if window is None:
        a.store(0x0008, 0x33)
        a.store(0x0009, 0x33)
    else:
        # by default: window 2 only: VDC 1, both windows: VDC 2 ($08); no window: VDC 2,
        # window 1 only: VDC 1 ($09)
        w1, w2, r08, r09 = (*window, 0x12, 0x21) if len(window) == 2 else window
        a.store(0x0008, r08)
        a.store(0x0009, r09)
        a.store(0x000A, w1 & 0xFF)
        a.store(0x000B, w1 >> 8)
        a.store(0x000C, w2 & 0xFF)
        a.store(0x000D, w2 >> 8)
    spin = a.here
    a.b(0x4C, spin & 0xFF, spin >> 8)  # JMP spin
    stub = a.here
    a.b(0x40)  # RTI
    image = bytearray([0xFF]) * 0x2000
    if len(a.code) > 0x1FF6:
        raise SystemExit(f"the probe is {len(a.code)} bytes")
    image[: len(a.code)] = a.code
    for offset, vector in (
        (0x1FF6, stub),
        (0x1FF8, stub),
        (0x1FFA, stub),
        (0x1FFC, stub),
        (0x1FFE, reset),
    ):
        image[offset : offset + 2] = bytes((vector & 0xFF, vector >> 8))
    return bytes(image)


def probes() -> dict[str, tuple[str, tuple[int, ...] | None]]:
    out: dict[str, tuple[str, tuple[int, ...] | None]] = {}
    for clock, pairs in WINDOWS.items():
        for n, pair in enumerate(pairs):
            out[f"win-{clock}-{n}"] = (clock, pair)
        out[f"clear-{clock}"] = (clock, None)
        # U-SGX2: any window area shows nothing (entry $000, both VDCs off), no window shows
        # VDC 1. Widths $40 and $20 (at or below $40: off), then $41 (one dot past the origin)
        out[f"off-{clock}"] = (clock, (0x40, 0x20, 0x00, 0x10))
        out[f"one-{clock}"] = (clock, (0x41, 0x00, 0x00, 0x10))
    return out


# -- measuring --------------------------------------------------------------------------------


def which(value: int) -> str:
    if value == 0x000:
        return "000"
    if value == 0x100:
        return "100"
    if 0x01 <= value <= 0x7F:
        return "V1"
    if 0x81 <= value <= 0xFF:
        return "V2"
    return f"{value:03x}"


def runs(row) -> list[tuple[str, int, int]]:
    """(class, first dot, length) runs of a row."""
    out: list[tuple[str, int, int]] = []
    for x, v in enumerate(row):
        c = which(int(v))
        if out and out[-1][0] == c:
            out[-1] = (c, out[-1][1], out[-1][2] + 1)
        else:
            out.append((c, x, 1))
    return out


def window_edges(pic, dx: int, dy: int) -> dict:
    """The VDC 2 -> VDC 1 and VDC 1 -> VDC 2 switches of every row, in our row dots (x + dx)."""
    found: dict[tuple[int, int], int] = {}
    for y in range(pic.shape[0]):
        seq = [r for r in runs(pic[y]) if r[0] in ("V1", "V2") and r[2] >= 4]
        for (c0, _, _), (c1, x1, _) in pairwise(seq):
            if (c0, c1) == ("V2", "V1"):
                key = ("e1", x1 + dx)
            elif (c0, c1) == ("V1", "V2"):
                key = ("e2", x1 + dx)
            else:
                continue
            found[key] = found.get(key, 0) + 1
    out: dict = {}
    for name in ("e1", "e2"):
        votes = {x: n for (k, x), n in found.items() if k == name}
        out[name] = max(votes, key=votes.get) if votes else None
        out[name + "_rows"] = votes.get(out[name], 0) if votes else 0
        out[name + "_others"] = sorted(x for x in votes if x != out[name])
    return out


def strips(pic, dx: int = 0) -> dict:
    """For the backdrop probe: the entry-$000 area's width on the middle row and its height in
    the middle column (in our dots: column x + dx). VDC 2's transparent value winning gives VDC 2's
    width (256 dots at 5 MHz) and VDC 2's height (192 lines); VDC 1's gives 224 and 224; "either
    transparent shows $000" gives VDC 2's width and VDC 1's height."""
    rows, cols = pic.shape
    y = rows // 2
    middle = [(c, int(x) + dx, int(n)) for c, x, n in runs(pic[y]) if n >= 4]
    width = max((n for c, _, n in middle if c == "000"), default=0)
    column = [r for r in runs(pic[:, cols // 2]) if r[0] == "000"]
    height = max((n for _, _, n in column), default=0)
    return {"middle_row": middle, "width_000": width, "height_000": int(height)}


def middle_row(pic, dx: int = 0) -> dict:
    """The middle row's runs (class, our dot, length), for the window-off probes."""
    return {"middle_row": [(c, int(x) + dx, int(n)) for c, x, n in runs(pic[pic.shape[0] // 2])]}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("scratch", type=Path)
    p.add_argument("results", type=Path)
    p.add_argument("--frames", type=int, default=60)
    p.add_argument("--only", default="")
    p.add_argument("--build-only", action="store_true")
    a = p.parse_args()
    a.scratch.mkdir(parents=True, exist_ok=True)
    base = Path(os.environ.get("PCENGINE_PYTHON", "/data/emu/pcengine-python"))
    sys.path.insert(0, str(base / "scripts"))
    import m2_compare as cmp
    import m2_refs

    for name, (clock, window) in probes().items():
        if a.only not in name:
            continue
        work = a.scratch / name
        work.mkdir(parents=True, exist_ok=True)
        image = work / f"{name}.sgx"
        image.write_bytes(build(clock, window))
        if a.build_only:
            continue
        ours = work / "ours.pkl"
        began = time.monotonic()
        cmd = ["nice", "-n", "10", str(PYPY), "-I", str(ROOT / "scripts/sgx_ours.py"), str(image),
               str(ours), "--frames", str(a.frames)]  # fmt: skip
        done = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if done.returncode:
            raise SystemExit(done.stderr)
        mine = cmp.ours_array(pickle.loads(ours.read_bytes())["rows"])
        rows = [{"probe": name, "judge": "ours", "clock": clock, "window": window,
                 "seconds": round(time.monotonic() - began, 1)}]  # fmt: skip
        if window is None:
            rows[0].update(strips(mine))
        elif len(window) == 4:
            rows[0].update(middle_row(mine))
        else:
            rows[0].update(window_edges(mine, 0, 0))
        for judge, stem in (("mesen_sprites", "mesen"), ("beetle", "beetle")):
            m2_refs.run_one(image, work, a.frames, judge)
            png = work / f"{stem}_{a.frames}.png"
            row = {"probe": name, "judge": stem, "clock": clock, "window": window}
            if not png.is_file():
                row["error"] = "no picture"
                rows.append(row)
                continue
            pic = cmp.nine_bit(png)
            _, dx, dy = cmp.best_alignment(pic, mine, range(-120, 200), range(-3, 4))
            px, equal_rows, first, _ = cmp.stats(pic, mine, dx, dy)
            row.update(dx=dx, dy=dy, px=round(px, 4), rows=round(equal_rows, 4), first=first,
                       shape=list(pic.shape))  # fmt: skip
            if window is None:
                row.update(strips(pic, dx))
            elif len(window) == 4:
                row.update(middle_row(pic, dx))
            else:
                row.update(window_edges(pic, dx, dy))
            rows.append(row)
        with a.results.open("a") as f:
            for row in rows:
                f.write(json.dumps(row, default=int) + "\n")
        for row in rows:
            brief = {k: row.get(k) for k in ("dx", "rows", "e1", "e2") if k in row}
            print(name, row["judge"], brief, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
