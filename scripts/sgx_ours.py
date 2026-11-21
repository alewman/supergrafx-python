#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run a SuperGrafx HuCard on this board for N frames and save the frame as 9-bit rows.

    .venv-pypy/bin/python scripts/sgx_ours.py CARD.sgx OUT.pkl [--frames 300] [--mode sgx|compat|base]
        [--vpc-option NAME=VALUE ...] [--press BUTTONS@FRAME+HOLD ...] [--also N,N,...]

`--mode sgx` is the add-on in native position; `compat` the back-panel switch in PC Engine
position; `base` is the **fallback**: the card on the plain pcengine-python board (one VDC, no
VPC, 32 KiB of RAM), i.e. the SuperGrafx as a base-board mode. `--vpc-option` sets a named class
attribute of `Vpc` (`PRIORITY_LABELS=sgxtech`). The picture is `capture.last_frame` after the N-th
frame: 242 rows of 9-bit palette values (the same format as the base board's m2_ours.py). Run it
under PyPy. The card is read in place. `--press` is scripted pad input in the base board's spelling
(its `scripts/presses.py`, loaded from the base repository's working tree: tooling, not chips);
`--also` saves earlier frames too, as OUT-<n>.pkl.
"""

from __future__ import annotations

import argparse
import os
import pickle
import sys
import time
from dataclasses import replace
from pathlib import Path

from pcengine_python import pads
from pcengine_python.board import Board
from pcengine_python.cards import card_from_path
from pcengine_python.system import build

from supergrafx_python import SUPERGRAFX, SuperGrafx, Vpc

BASE = Path(
    os.environ.get("PCENGINE_PYTHON", Path(__file__).resolve().parents[2] / "pcengine-python")
)
sys.path.insert(0, str(BASE / "scripts"))
import presses as press_script  # noqa: E402


def make(mode: str, card, options: dict[str, str], pad):
    if mode == "base":
        # The fallback: a machine row with 32 KiB and the one VDC, nothing else.
        row = replace(SUPERGRAFX, name="SuperGrafx (base mode)", vdc_count=1)
        board = Board(row, card=card, pad=pad)
        return board, build(board), None
    vpc = Vpc()
    for name, value in options.items():
        current = getattr(vpc, name)
        setattr(vpc, name, type(current)(value) if isinstance(current, str) else eval(value))
    sg = SuperGrafx(card=card, compat=mode == "compat", vpc=vpc, pad=pad)
    return sg.board, sg.build(), sg


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("card", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--frames", type=int, default=300)
    p.add_argument("--mode", choices=("sgx", "compat", "base"), default="sgx")
    p.add_argument("--vpc-option", action="append", default=[], metavar="NAME=VALUE")
    p.add_argument("--press", action="append", default=[], metavar="BUTTONS@FRAME+HOLD")
    p.add_argument("--also", default="", help="comma list of earlier frames to save as well")
    p.add_argument(
        "--trace-vpc",
        type=int,
        default=0,
        metavar="N",
        help="print every VPC write of the last N frames: frame, line, dot, register, value",
    )
    a = p.parse_args()
    options = dict(o.split("=", 1) for o in a.vpc_option)
    pad = pads.Pad2()
    presses = press_script.parse(a.press)
    also = {int(n) for n in a.also.split(",") if n}
    board, system, sg = make(a.mode, card_from_path(a.card), options, pad)
    began = time.monotonic()
    writes: dict[int, int] = {}
    if sg is not None:
        original = sg.vpc.write

        def counted(offset, value, mclk):
            writes[offset & 15] = writes.get(offset & 15, 0) + 1
            tl = board.timeline
            if a.trace_vpc and tl.frame >= a.frames - a.trace_vpc:
                dot = (mclk - tl.line_start - 237) // board.vce.dot_divider
                print(
                    f"VPC write frame {tl.frame} line {tl.line} dot {dot}: ${offset & 15:02X} <- ${value:02X}"
                )
            original(offset, value, mclk)

        sg.vpc.write = counted

    def save(out: Path) -> None:
        frame = board.capture.last_frame
        with out.open("wb") as f:
            pickle.dump(
                {"rows": frame.rows, "dividers": frame.dividers, "number": board.timeline.frame}, f
            )

    for n in range(a.frames):
        pad.pressed = press_script.board_mask(press_script.held(presses, n))
        system.run_frame()
        if n + 1 in also:
            save(a.out.with_name(f"{a.out.stem}-{n + 1}{a.out.suffix}"))
    save(a.out)
    frame = board.capture.last_frame
    vpc = (
        f", VPC {[hex(x) for x in sg.vpc.priority]} windows {sg.vpc.window}, "
        f"writes by register { {f'${r:02X}': n for r, n in sorted(writes.items())} }, "
        f"VDC2 VRAM words set {sum(1 for w in sg.vdc2.vram if w)}"
        if sg
        else ""
    )
    print(
        f"{a.card.name} [{a.mode}]: {a.frames} frames in {time.monotonic() - began:.1f} s, "
        f"{len(frame.rows)} rows of {len(frame.rows[0])} dots, VCE control {board.vce.control:#04x}{vpc}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
