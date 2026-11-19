# SPDX-License-Identifier: MIT
"""Small drivers for the board-level tests (the base board's own fakes live in its tests)."""

from __future__ import annotations

from pcengine_python.machine import HARDWARE_BASE
from pcengine_python.sockets import VideoTiming

VIDEO = HARDWARE_BASE  # $FF:0000
VCE = HARDWARE_BASE + 0x0400


class ScriptedCpu:
    """Drives a board's bus one callback per CPU cycle, as the core does. `_opcode` is what the
    core keeps for the instruction it last fetched; a test sets it to make a write an ST."""

    def __init__(self, board, *, high_speed: bool = False) -> None:
        self.board = board
        self.high_speed = high_speed
        self.irq_disable = 0
        self.lines = (False, False, False)
        self._opcode = 0
        board.attach_cpu(self)

    def set_irq_lines(self, irq1: bool, irq2: bool, tiq: bool) -> None:
        self.lines = (irq1, irq2, tiq)

    def read(self, address: int) -> int:
        return self.board.read_byte(address)

    def write(self, address: int, value: int, opcode: int = 0x8D) -> None:
        self._opcode = opcode
        self.board.write_byte(address, value)

    def idle(self, cycles: int = 1) -> None:
        for _ in range(cycles):
            self.board.idle(None)


def timing(divider: int = 4, line: int = 20) -> VideoTiming:
    return VideoTiming(
        frame=0, line=line, start_mclk=0, dot_divider=divider, frame_lines=263, in_vsync=False
    )


def vdc_reg(cpu, base, register, value16, opcode=0x8D):
    """Select a VDC register and write its 16 bits through the bus at `base` (a VDC's port 0)."""
    cpu.write(base + 0, register, opcode)
    cpu.write(base + 2, value16 & 0xFF, opcode)
    cpu.write(base + 3, value16 >> 8, opcode)


def standard_display(cpu, base, *, cr=0x00C8):
    """The 256x224 mode of pcetech 7 (see the base board's tests/helpers.py)."""
    vdc_reg(cpu, base, 0x0A, 0x0202)  # HSR
    vdc_reg(cpu, base, 0x0B, 0x041F)  # HDR
    vdc_reg(cpu, base, 0x0C, 0x1702)  # VPR
    vdc_reg(cpu, base, 0x0D, 0x00DF)  # VDW
    vdc_reg(cpu, base, 0x0E, 0x000C)  # VCR
    vdc_reg(cpu, base, 0x05, cr)  # CR


class PublicOpcodeCpu(ScriptedCpu):
    """A ScriptedCpu of a core that publishes `opcode` (and, here, nothing a fallback could use)."""

    def __init__(self, board, **kwargs) -> None:
        super().__init__(board, **kwargs)
        self.opcode = self._opcode
        del self._opcode

    def write(self, address: int, value: int, opcode: int = 0x8D) -> None:
        self.opcode = opcode
        self.board.write_byte(address, value)
