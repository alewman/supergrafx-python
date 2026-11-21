# SPDX-License-Identifier: MIT
"""The add-on with VDC 2 idle is the base board: same rows as the fallback (base mode).

Power-up leaves the VPC at `$11 $11 ...` (windows off, VDC 1 only), so a program that never touches
VDC 2 or the VPC must draw what the one-VDC board draws. Uses the Covell CPU test the base board
fetches (read in place; skipped when absent)."""

import os
from dataclasses import replace
from pathlib import Path

import pytest
from pcengine_python import pads
from pcengine_python.board import Board
from pcengine_python.cards import card_from_path
from pcengine_python.system import build

from supergrafx_python import SUPERGRAFX, SuperGrafx

# The base board's fetched test card (its scripts/fetch_references.py), in its checkout.
BASE = Path(
    os.environ.get("PCENGINE_PYTHON", Path(__file__).resolve().parents[2] / "pcengine-python")
)
CARD = BASE / "tests/test_roms/CPU_Test/CPU_Test_10.pce"
FRAMES = 4


@pytest.mark.skipif(not CARD.exists(), reason="the base board's fetched CPU test is absent")
def test_idle_vdc2_and_default_vpc_draw_what_the_base_mode_draws():
    base = Board(replace(SUPERGRAFX, vdc_count=1), card=card_from_path(CARD), pad=pads.Pad2())
    base_system = build(base)
    sg = SuperGrafx(card=card_from_path(CARD), pad=pads.Pad2())
    system = sg.build()
    for _ in range(FRAMES):
        base_system.run_frame()
        system.run_frame()
        assert sg.board.capture.last_frame.rows == base.capture.last_frame.rows
    assert sg.board.mclk == base.mclk
