#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The five SuperGrafx cards on MAME `sgx` against this board, crudely (M6, a detector).

    python3 -I scripts/sgx_mame.py LIBDIR SCRATCH RESULTS.jsonl [--only SUBSTR] [--seconds 5]

MAME draws a different geometry (1088 columns, about 5 rows' offset), so no pixel comparison is
possible; the base board's `detectors_compare` statistics are used instead: `tv` (total variation of
the 3-bit colour histograms of the middle rows) and `rows` (share of rows whose dominant colour agrees
at the best vertical offset). Ours is run to `seconds * 60` frames. One card at a time, niced.
Needs numpy and Pillow (the system python3).
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BASE = Path(
    os.environ.get("PCENGINE_PYTHON", Path(__file__).resolve().parents[2] / "pcengine-python")
)
sys.path.insert(0, str(BASE / "scripts"))
import detectors_compare as dc  # noqa: E402
import m5_sweep  # noqa: E402

PYPY = ROOT / ".venv-pypy/bin/python"


def ours_image(pkl: Path) -> Image.Image:
    """Ours as an RGB picture through the same linear 3-bit table the detectors are quantised to."""
    rows = pickle.loads(pkl.read_bytes())["rows"]
    img = Image.new("RGB", (len(rows[0]), len(rows)))
    px = img.load()
    for y, row in enumerate(rows):
        for x, value in enumerate(row):
            g, r, b = (value >> 6) & 7, (value >> 3) & 7, value & 7
            px[x, y] = (r * 255 // 7, g * 255 // 7, b * 255 // 7)
    return img


def one(card: Path, scratch: Path, seconds: int, mode: str) -> dict:
    work = scratch / re.sub(r"\W+", "_", card.stem)
    out: dict = {"card": card.name, "mode": mode, "seconds": seconds, "detector": "mame sgx"}
    try:
        image = m5_sweep.extract(card, work / "rom")
        mame = work / "mame"
        subprocess.run(["nice", "-n", "10", sys.executable, "-I", str(BASE / "scripts/mame_trace.py"),
                        "sgx", str(image), "--no-trace", "--seconds", str(seconds), "--out", str(mame)],
                       capture_output=True, check=False)  # fmt: skip
        snaps = sorted((mame / "snap").rglob("*.png"))
        if not snaps:
            raise RuntimeError("MAME wrote no snapshot")
        pkl = work / "ours.pkl"
        run = subprocess.run(["nice", "-n", "10", str(PYPY), "-I", str(ROOT / "scripts/sgx_ours.py"),
                              str(image), str(pkl), "--frames", str(seconds * 60), "--mode", mode],
                             capture_output=True, text=True, check=False)  # fmt: skip
        if run.returncode:
            raise RuntimeError(run.stderr.strip().splitlines()[-1] if run.stderr else "failed")
        tv, rows, off = dc.compare(dc.quant(Image.open(snaps[-1])), dc.quant(ours_image(pkl)))
        out.update(tv=round(tv, 3), rows=round(rows, 3), offset=off)
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
    p.add_argument("--seconds", type=int, default=5)
    p.add_argument("--mode", default="sgx", choices=("sgx", "compat", "base"))
    a = p.parse_args()
    a.scratch.mkdir(parents=True, exist_ok=True)
    for card in sorted(
        c
        for c in a.lib.iterdir()
        if c.suffix.lower() in {".7z", ".zip", ".sgx"} and a.only in c.name
    ):
        row = one(card, a.scratch, a.seconds, a.mode)
        with a.results.open("a") as f:
            f.write(json.dumps(row) + "\n")
        print(row, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
