# SPDX-License-Identifier: MIT
"""Save states: the base board's `state.py` over the SuperGrafx (the VPC, the page, both VDCs)."""

import json
import zlib

import pytest
from pcengine_python.board import Board
from pcengine_python.cards import RomCard
from pcengine_python.state import StateError, load_state, save_state
from pcengine_python.system import build

from supergrafx_python import SuperGrafx


def image(fill=0xEA):
    """A card that is only NOPs and its reset vector (to $E000)."""
    data = bytearray([fill]) * 0x2000
    data[-2:] = b"\x00\xe0"
    return bytes(data)


def running(**kwargs):
    sg = SuperGrafx(card=RomCard(image()), **kwargs)
    return sg, sg.build()


def test_the_vpc_the_page_and_the_second_vdc_come_back():
    sg, system = running()
    sg.vpc.priority[:] = [0x75, 0x56]
    sg.vpc.window[:] = [0x123, 0x3FF]
    sg.vdc2.vram[0x1234] = 0xBEEF
    sg.vdc2.regs.select = 0x09
    sg.compat = True
    for _ in range(2000):
        system.step()
    other, loaded = running()
    load_state(loaded, save_state(system))
    assert other.vpc.priority == [0x75, 0x56] and other.vpc.window == [0x123, 0x3FF]
    assert other.vdc2.vram[0x1234] == 0xBEEF and other.vdc2.regs.select == 0x09
    assert other.compat is True
    assert other.board.capture.path is other.vpc and other.board.vdcs[1] is other.vdc2  # wiring
    assert save_state(loaded) == save_state(system)
    for _ in range(2000):
        system.step()
        loaded.step()
    assert save_state(loaded) == save_state(system)


def test_a_state_names_this_package_and_a_plain_board_refuses_it():
    _sg, system = running()
    state = save_state(system)
    assert "supergrafx_python" in json.loads(zlib.decompress(state))["packages"]
    with pytest.raises(StateError, match="of the SuperGrafx, not the PC Engine"):
        load_state(build(Board(card=RomCard(image()))), state)
