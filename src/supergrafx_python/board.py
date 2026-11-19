# SPDX-License-Identifier: MIT
"""The SuperGrafx: the pinned PC Engine board with a machine row, a VPC and a second VDC.

Nothing here is copied from `pcengine-python`; this module only composes it through its sockets
(docs/start-here.md lists them):

- socket 12 (instances) and the machine row: `Machine.vdc_count = 2` makes the board build, run,
  sync and read a second `Vdc` and OR its IRQ1 (docs/issues/0001 of the base board);
- socket 3 (the decode): `VideoPage` claims `$FF:0000-03FF` over the VDC page;
- socket 7 (pixel path): `Vpc.mix` is the board's `PixelPath`;
- the work RAM is the machine row's 32 KiB, mirrored nowhere (banks `$F8-$FB`).
"""

from __future__ import annotations

from pcengine_python.board import Board
from pcengine_python.machine import HARDWARE_FIRST_PAGE
from pcengine_python.sockets import ResetKind
from pcengine_python.system import System, build

from supergrafx_python.machine import SUPERGRAFX
from supergrafx_python.vpc import VideoPage, Vpc

# [hw: HuC6280 hardware manual] ST0, ST1, ST2 are opcodes $03, $13, $23.
ST_OPCODES = (0x03, 0x13, 0x23)


class SuperGrafx:
    """A base board configured as a SuperGrafx. `board` is the plain `pcengine_python.Board`."""

    def __init__(self, card=None, *, compat: bool = False, vpc: Vpc | None = None, **board_kwargs):
        """`compat=True` is the back-panel switch in PC Engine position. `board_kwargs` go to
        `Board` (pad, port, power_on_seed, start_line, ...)."""
        self.vpc = vpc if vpc is not None else Vpc()
        self.board = Board(SUPERGRAFX, card=card, pixel_path=self.vpc, **board_kwargs)
        self.vdc1, self.vdc2 = self.board.vdcs
        self.page = VideoPage(
            self.vdc1, self.vdc2, self.vpc, store_immediate=self._store_immediate, compat=compat
        )
        # The VPC decodes the whole 1 KiB video chip area: four pages of the hardware page.
        self.board.pages.claim(HARDWARE_FIRST_PAGE, HARDWARE_FIRST_PAGE + 3, self.page)

    @property
    def compat(self) -> bool:
        return self.page.compat

    @compat.setter
    def compat(self, value: bool) -> None:
        self.page.compat = value

    def _store_immediate(self) -> bool:
        """Is the CPU's current cycle the write of an ST0/ST1/ST2? The VPC sees the instruction
        (docs/issues/0001, "Still open"). Newer cores publish `HuC6280.opcode`; the core this
        board is pinned to (via pcengine-python) only keeps the private `_opcode`, so fall back."""
        cpu = self.board.cpu
        if cpu is None:
            return False
        opcode = getattr(cpu, "opcode", None)
        if opcode is None:
            opcode = getattr(cpu, "_opcode", None)
        return opcode in ST_OPCODES

    def reset(self, kind: ResetKind) -> None:
        self.board.reset(kind)
        if kind is ResetKind.POWER_ON:
            self.vpc.reset()

    def build(self, cpu_class: type | None = None) -> System:
        """The real HuC6280 core on this board."""
        return build(self.board, cpu_class)
