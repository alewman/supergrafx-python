#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The five SuperGrafx cards against Mesen2 and Beetle PCE, one niced run at a time (M6).

    python3 -I scripts/sgx_pictures.py LIBDIR SCRATCH RESULTS.jsonl [--only SUBSTR]
        [--target 300] [--window 3] [--mode sgx] [--vpc-option NAME=VALUE ...]
        [--press BUTTONS@FRAME+HOLD ...]

Needs numpy and Pillow: the system python3 (the venvs lack them); the board runs under
`.venv-pypy`. For each card in LIBDIR (read in place; the image is extracted into SCRATCH and
removed after): ours to frame `target`, then Mesen2 (sprites on) and Beetle PCE over frames
target-W..target+W, and the comparison at the 9-bit palette value after the detectors'
alignment offsets, exactly as the base board's M5 sweep does (its `compare`/`best_frame_exact`
are imported from the pinned base repository's scripts: tooling, not chips). One JSON line per
card. `--press` gives the same scripted pad input (the base board's `scripts/presses.py`) to the
board and to both detectors, for a frame past the title screen. **No parallelism**: detectors run one after the other under `nice -n 10`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = Path(
    os.environ.get("PCENGINE_PYTHON", Path(__file__).resolve().parents[2] / "pcengine-python")
)
sys.path.insert(0, str(BASE / "scripts"))
import m2_refs  # noqa: E402
import m5_sweep  # noqa: E402

PYPY = ROOT / ".venv-pypy/bin/python"
IMAGE = {".sgx", ".pce"}


def remove_tree(path: Path) -> None:
    m5_sweep.remove_tree(path)


def extract(archive: Path, into: Path) -> Path:
    return m5_sweep.extract(archive, into)


def one(
    card: Path,
    scratch: Path,
    target: int,
    window: int,
    mode: str,
    options: list[str],
    presses: list[str],
) -> dict:
    work = scratch / re.sub(r"\W+", "_", card.stem)
    out: dict = {"card": card.name, "mode": mode, "target": target, "options": options}
    if presses:
        out["presses"] = presses
    try:
        image = extract(card, work / "rom")
        began = time.monotonic()
        ours = work / "ours.pkl"
        cmd = ["nice", "-n", "10", str(PYPY), "-I", str(ROOT / "scripts/sgx_ours.py"), str(image),
               str(ours), "--frames", str(target), "--mode", mode]  # fmt: skip
        for o in options:
            cmd += ["--vpc-option", o]
        for spec in presses:
            cmd += ["--press", spec]
        run = subprocess.run(cmd, capture_output=True, text=True, check=False)
        out["ours_seconds"] = round(time.monotonic() - began, 1)
        if run.returncode:
            raise RuntimeError(run.stderr.strip().splitlines()[-1] if run.stderr else "failed")
        out["ours_log"] = run.stdout.strip()
        refs = work / "refs"
        refs.mkdir(parents=True, exist_ok=True)
        for n in range(target - window, target + window + 1):
            for which in ("mesen_sprites", "beetle"):  # one after the other
                m2_refs.run_one(image, refs, n, which, tuple(presses))
        m5_sweep.TARGETS = (target, target)
        out.update(m5_sweep.compare(ours, refs, target))
        out["size"] = image.stat().st_size
    except Exception as e:  # recorded, not hidden
        out["error"] = f"{type(e).__name__}: {e}"
    finally:
        if work.exists():
            remove_tree(work)
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("lib", type=Path)
    p.add_argument("scratch", type=Path)
    p.add_argument("results", type=Path)
    p.add_argument("--only", default="")
    p.add_argument("--target", type=int, default=300)
    p.add_argument("--window", type=int, default=3)
    p.add_argument("--mode", default="sgx", choices=("sgx", "compat", "base"))
    p.add_argument("--vpc-option", action="append", default=[], metavar="NAME=VALUE")
    p.add_argument("--press", action="append", default=[], metavar="BUTTONS@FRAME+HOLD")
    a = p.parse_args()
    a.scratch.mkdir(parents=True, exist_ok=True)
    cards = sorted(
        c
        for c in a.lib.iterdir()
        if c.suffix.lower() in IMAGE | {".7z", ".zip"} and a.only in c.name
    )
    for card in cards:
        row = one(card, a.scratch, a.target, a.window, a.mode, a.vpc_option, a.press)
        with a.results.open("a") as f:
            f.write(json.dumps(row, default=int) + "\n")
        brief = (
            {k: (row.get(k) or {}).get("rows") for k in ("mesen", "beetle")}
            if "error" not in row
            else row["error"]
        )
        print(card.name, a.mode, brief, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
