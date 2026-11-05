#!/usr/bin/env python3
"""Run a SuperGrafx HuCard on this board for N frames and save the frame as 9-bit rows.

    .venv-pypy/bin/python scripts/sgx_ours.py CARD.sgx OUT.pkl [--frames 300] [--mode sgx|compat|base]
        [--vpc-option NAME=VALUE ...]

`--mode sgx` is the add-on in native position; `compat` the back-panel switch in PC Engine
position; `base` is the **fallback**: the card on the plain pcengine-python board (one VDC, no
VPC, 32 KiB of RAM), i.e. the SuperGrafx as a base-board mode. `--vpc-option` sets a named class
attribute of `Vpc` (`PRIORITY_LABELS=sgxtech`). The picture is `capture.last_frame` after the N-th
frame: 242 rows of 9-bit palette values (the same format as the base board's m2_ours.py). Run it
under PyPy. The card is read in place.
"""

from __future__ import annotations

import argparse
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


def make(mode: str, card, options: dict[str, str]):
    if mode == "base":
        # The fallback: a machine row with 32 KiB and the one VDC, nothing else.
        row = replace(SUPERGRAFX, name="SuperGrafx (base mode)", vdc_count=1)
        board = Board(row, card=card, pad=pads.Pad2())
        return board, build(board), None
    vpc = Vpc()
    for name, value in options.items():
        current = getattr(vpc, name)
        setattr(vpc, name, type(current)(value) if isinstance(current, str) else eval(value))
    sg = SuperGrafx(card=card, compat=mode == "compat", vpc=vpc, pad=pads.Pad2())
    return sg.board, sg.build(), sg


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("card", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--frames", type=int, default=300)
    p.add_argument("--mode", choices=("sgx", "compat", "base"), default="sgx")
    p.add_argument("--vpc-option", action="append", default=[], metavar="NAME=VALUE")
    p.add_argument(
        "--trace-vpc",
        type=int,
        default=0,
        metavar="N",
        help="print every VPC write of the last N frames: frame, line, dot, register, value",
    )
    a = p.parse_args()
    options = dict(o.split("=", 1) for o in a.vpc_option)
    board, system, sg = make(a.mode, card_from_path(a.card), options)
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
    for _ in range(a.frames):
        system.run_frame()
    frame = board.capture.last_frame
    with a.out.open("wb") as f:
        pickle.dump(
            {"rows": frame.rows, "dividers": frame.dividers, "number": board.timeline.frame}, f
        )
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
