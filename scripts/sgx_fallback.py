#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Measure the base-mode fallback: each SuperGrafx card as the add-on and through the plain board.

    python3 -I scripts/sgx_fallback.py LIBDIR SCRATCH RESULTS.jsonl [--only SUBSTR] [--frames 300]

The add-on (`sgx_ours.py --mode sgx`) and the fallback (`--mode base`: pcengine-python with a
32 KiB machine row, one VDC, no VPC) each run the card to the same frame, one after the other
under `nice`. The two pictures are compared at the 9-bit palette value (equal pixels, equal rows,
first difference). Where they differ the card needs the VPC or the second VDC (and the detectors
decide which picture is right: sgx_pictures.py). Needs numpy (the system python3).
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = Path(
    os.environ.get("PCENGINE_PYTHON", Path(__file__).resolve().parents[2] / "pcengine-python")
)
sys.path.insert(0, str(BASE / "scripts"))
import m5_sweep  # noqa: E402

PYPY = ROOT / ".venv-pypy/bin/python"


def run(image: Path, out: Path, frames: int, mode: str) -> tuple[float, str]:
    began = time.monotonic()
    cmd = ["nice", "-n", "10", str(PYPY), "-I", str(ROOT / "scripts/sgx_ours.py"), str(image),
           str(out), "--frames", str(frames), "--mode", mode]  # fmt: skip
    done = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if done.returncode:
        raise RuntimeError(done.stderr.strip().splitlines()[-1] if done.stderr else "failed")
    return time.monotonic() - began, done.stdout.strip()


def one(card: Path, scratch: Path, frames: int) -> dict:
    work = scratch / re.sub(r"\W+", "_", card.stem)
    out: dict = {"card": card.name, "frames": frames}
    try:
        image = m5_sweep.extract(card, work / "rom")
        seconds, log = run(image, work / "sgx.pkl", frames, "sgx")
        out.update(sgx_seconds=round(seconds, 1), sgx_log=log)
        seconds, log = run(image, work / "base.pkl", frames, "base")
        out.update(base_seconds=round(seconds, 1), base_log=log)
        a = np.array(pickle.loads((work / "sgx.pkl").read_bytes())["rows"], dtype=np.uint16)
        b = np.array(pickle.loads((work / "base.pkl").read_bytes())["rows"], dtype=np.uint16)
        if a.shape != b.shape:
            out["shape"] = [list(a.shape), list(b.shape)]
        else:
            equal = a == b
            differ = np.argwhere(~equal)
            out.update(
                px=round(float(equal.mean()), 5),
                rows=round(float(equal.all(axis=1).mean()), 4),
                differing_rows=int((~equal.all(axis=1)).sum()),
                first=[int(differ[0][0]), int(differ[0][1]), int(a[tuple(differ[0])]),
                       int(b[tuple(differ[0])])] if len(differ) else None,
            )  # fmt: skip
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
    finally:
        if work.exists():
            m5_sweep.remove_tree(work)
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("lib", type=Path)
    p.add_argument("scratch", type=Path)
    p.add_argument("results", type=Path)
    p.add_argument("--only", default="")
    p.add_argument("--frames", type=int, default=300)
    a = p.parse_args()
    a.scratch.mkdir(parents=True, exist_ok=True)
    cards = sorted(
        c
        for c in a.lib.iterdir()
        if c.suffix.lower() in {".7z", ".zip", ".sgx"} and a.only in c.name
    )
    for card in cards:
        row = one(card, a.scratch, a.frames)
        with a.results.open("a") as f:
            f.write(json.dumps(row) + "\n")
        print(
            {k: row.get(k) for k in ("card", "px", "rows", "differing_rows", "first", "error")},
            flush=True,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
