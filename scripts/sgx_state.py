#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Save states on the SuperGrafx: a run saved and loaded continues as the run that wasn't.

    .venv-pypy/bin/python scripts/sgx_state.py CARD.sgx... [--at 300] [--to 360] [--extra 777]
        [--mode sgx|compat] [--press BUTTONS@FRAME+HOLD ...]

The check is the base board's (`scripts/state_roundtrip.py`, loaded from the base repository's
working tree: tooling, not chips): every CPU bus cycle, the mixed picture, the audio and the CPU's
state of every frame after the save, on a fresh machine and on one that had run. The state itself is
`pcengine_python.state`: this package only registers its classes (the VPC, the video page).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from pcengine_python import pads
from pcengine_python.cards import card_from_path

from supergrafx_python import SuperGrafx

BASE = Path(
    os.environ.get("PCENGINE_PYTHON", Path(__file__).resolve().parents[2] / "pcengine-python")
)
sys.path.insert(0, str(BASE / "scripts"))
import presses as press_script  # noqa: E402
from state_roundtrip import roundtrip  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("cards", type=Path, nargs="+")
    p.add_argument("--at", type=int, default=300)
    p.add_argument("--to", type=int, default=360)
    p.add_argument("--extra", type=int, default=777, help="instructions past frame --at")
    p.add_argument("--mode", choices=("sgx", "compat"), default="sgx")
    p.add_argument("--press", action="append", default=[], metavar="BUTTONS@FRAME+HOLD")
    a = p.parse_args()
    failed = 0
    for card in a.cards:

        def make(card: Path = card):
            pad = pads.Pad2()
            sg = SuperGrafx(card=card_from_path(card), compat=a.mode == "compat", pad=pad)
            return sg.board, sg.build, pad

        ok, what = roundtrip(make, a.at, a.to, a.extra, press_script.parse(a.press))
        print(f"{'ok  ' if ok else 'FAIL'} {card.name} [{a.mode}]: {what}", flush=True)
        failed += not ok
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
