"""The HuC6202 video priority controller (VPC): the SuperGrafx's pixel path and its register block.

[hw: sgxtech, "Video Priority Controller"] The VPC

- mixes the 9-bit pixel buses of VDC 1 and VDC 2 and hands the result to the VCE
  (`Vpc.mix`, the board's `PixelPath` socket 7: one row per VDC, one row back);
- keeps two window widths and four 4-bit (enable, enable, priority) groups, one per window area;
- steers `ST0`-`ST2` to VDC 2 when `$0E` bit 0 is set (`Vpc.st_to_vdc2`, used by `VideoPage`);
- decodes the video chip area `$FF:0000-03FF` (`VideoPage`, with the compat switch).

A VDC row value is 9 bits: bit 8 sprite, bits 7-4 palette, bits 3-0 colour; a colour of 0 is
transparent. "Priority between backgrounds and sprites is managed internally to the VDC": the VPC
sees only the bit-8 sprite flag and the transparency, so it cannot tell a high-priority sprite from
a low one.

Everything the sources do not settle is a **named class attribute** with a provisional default and
its tier, so a later judge changes one line (docs/m6-record.md lists them as U/C entries).
"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import pairwise

from pcengine_python.machine import HSYNC_CLOCKS, LINE_CLOCKS
from pcengine_python.sockets import VideoTiming

SPRITE = 0x100  # bit 8 of a VDC row value: the pixel came from a sprite
COLOUR = 0x0F  # bits 3-0: 0 is transparent

# Register offsets inside the VPC block ($FF:0008-000F, native mode).
PRIORITY_A = 0x08  # bits 7-4 window 2 only, bits 3-0 windows 1 and 2 overlapping
PRIORITY_B = 0x09  # bits 7-4 no window, bits 3-0 window 1 only
WINDOW1_LSB, WINDOW1_MSB = 0x0A, 0x0B
WINDOW2_LSB, WINDOW2_MSB = 0x0C, 0x0D
ST_STEER = 0x0E  # bit 0: ST0-ST2 go to VDC 2


class Vpc:
    """Registers, ST steering and the mix. `mix(timing, rows)` is the PixelPath."""

    #: C-SGX1 (undecidable without hardware): which 2-bit priority code means what. sgxtech says
    #: 01b = "VDC #1 sprites behind the VDC #2 background" and 10b = "VDC #2 sprites in front of
    #: the VDC #1 background"; Mednafen and Mesen2 (tier 5) read the same register the other way
    #: round, and Mednafen's source says Dai Makai Mura (Ghouls 'n Ghosts) *uses setting 1 and
    #: expects VDC #2 sprites in front of the VDC #1 background*. A shipped game that works on
    #: hardware outranks the document's labels, so the default follows the detectors. "sgxtech"
    #: swaps the two codes. Tier: detectors + a game's behaviour (5), against tier 2 text.
    PRIORITY_LABELS = "detectors"

    #: U-SGX1: where the window edges fall. A window of width W covers the row's dots
    #: [0, W - 0x40 + ORIGIN[dot_divider]) and is off for W <= 0x40 (sgxtech: "values smaller
    #: than $0040 disable the window"; "windows start from the leftmost pixel of the physical
    #: screen"). The origin per dot clock (4 = 5.37 MHz, 3 = 7.16, 2 = 10.7) is Mednafen's
    #: calibrated `8 + 24`/`8 + 38`; Mesen2 uses 48 at every clock. Tier 5; the pictures decide
    #: (docs/m6-record.md).
    WINDOW_ORIGIN = {4: 32, 3: 46, 2: 32}  # noqa: RUF012

    #: U-SGX2: a window width at or below this disables the window (sgxtech, tier 2).
    WINDOW_OFF_AT_OR_BELOW = 0x40

    #: U-SGX3: the dot, counted from the end of the line's horizontal sync, at which a register
    #: write takes effect is the first dot whose time is at or after the write (the same rule as
    #: the VCE's palette); Mesen2 and Mednafen both draw the line up to the write first.
    #: (Documented behaviour of this model, tier 5; not a class switch.)

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """[hw: sgxtech] power-up: `$11 $11 $00 $00 $00 $00 $00 $00` in `$08-$0F`: windows off,
        store-immediate to VDC 1, and only VDC 1 enabled with the default priority everywhere."""
        self.priority = [0x11, 0x11]
        self.window = [0, 0]
        self.st_to_vdc2 = False
        self._shadow_priority = [0x11, 0x11]
        self._shadow_window = [0, 0]
        # (mclk, register, value) of every write that changes the picture, drained by `mix`
        self._log: list[tuple[int, int, int]] = []

    # -- the CPU's port -----------------------------------------------------------------------

    def read(self, offset: int) -> int:
        """`$08-$0F`. Both priority registers and the window LSBs return what was written; the
        window MSBs keep only bits 1-0; `$0E` and `$0F` read $00 [hw: sgxtech]."""
        reg = offset & 0x0F
        if reg == PRIORITY_A:
            return self.priority[0]
        if reg == PRIORITY_B:
            return self.priority[1]
        if reg == WINDOW1_LSB:
            return self.window[0] & 0xFF
        if reg == WINDOW1_MSB:
            return self.window[0] >> 8
        if reg == WINDOW2_LSB:
            return self.window[1] & 0xFF
        if reg == WINDOW2_MSB:
            return self.window[1] >> 8
        return 0x00

    def write(self, offset: int, value: int, mclk: int) -> None:
        reg = offset & 0x0F
        if reg == PRIORITY_A:
            self.priority[0] = value
        elif reg == PRIORITY_B:
            self.priority[1] = value
        elif reg == WINDOW1_LSB:
            self.window[0] = (self.window[0] & 0x300) | value
        elif reg == WINDOW1_MSB:
            self.window[0] = (self.window[0] & 0x0FF) | ((value & 3) << 8)
        elif reg == WINDOW2_LSB:
            self.window[1] = (self.window[1] & 0x300) | value
        elif reg == WINDOW2_MSB:
            self.window[1] = (self.window[1] & 0x0FF) | ((value & 3) << 8)
        elif reg == ST_STEER:
            self.st_to_vdc2 = bool(value & 1)
            return
        else:
            return  # $0F is unused
        self._log.append((mclk, reg, value))

    # -- the mix ------------------------------------------------------------------------------

    def mix(self, timing: VideoTiming, rows: Sequence[Sequence[int]]) -> list[int]:
        """The PixelPath: VDC 1's and VDC 2's rows for one line in, the row for the VCE out.

        A register written during the line takes effect at the first dot whose time is at or
        after the write, as the VCE's palette does (`Capture`): the line is mixed in pieces."""
        vdc1, vdc2 = rows[0], rows[1]
        dots = len(vdc1)
        div = timing.dot_divider
        first = timing.start_mclk + HSYNC_CLOCKS
        end = first + LINE_CLOCKS
        log = self._log
        used = 0
        while used < len(log) and log[used][0] < end:
            used += 1
        if not used:
            return self._span(vdc1, vdc2, 0, dots, div)
        out: list[int] = []
        x = 0
        for when, reg, value in log[:used]:
            stop = min(dots, max(x, -((first - when) // div)))  # ceil((when - first) / div)
            if stop > x:
                out += self._span(vdc1, vdc2, x, stop, div)
                x = stop
            self._replay(reg, value)
        out += self._span(vdc1, vdc2, x, dots, div)
        del log[:used]
        return out

    def _replay(self, reg: int, value: int) -> None:
        if reg == PRIORITY_A:
            self._shadow_priority[0] = value
        elif reg == PRIORITY_B:
            self._shadow_priority[1] = value
        elif reg in (WINDOW1_LSB, WINDOW1_MSB):
            keep = 0x300 if reg == WINDOW1_LSB else 0x0FF
            self._shadow_window[0] = (self._shadow_window[0] & keep) | (
                value if reg == WINDOW1_LSB else (value & 3) << 8
            )
        else:
            keep = 0x300 if reg == WINDOW2_LSB else 0x0FF
            self._shadow_window[1] = (self._shadow_window[1] & keep) | (
                value if reg == WINDOW2_LSB else (value & 3) << 8
            )

    def window_edge(self, width: int, div: int, dots: int) -> int:
        """The first row dot outside a window of register value `width` (0 = no window)."""
        if width <= self.WINDOW_OFF_AT_OR_BELOW:
            return 0
        return min(dots, width - 0x40 + self.WINDOW_ORIGIN[div])

    def region_config(self, in_window1: bool, in_window2: bool) -> int:
        """The 4-bit group for a window area, from the registers as the line has replayed them."""
        a, b = self._shadow_priority
        if in_window1 and in_window2:
            return a & 0x0F
        if in_window2:
            return a >> 4
        if in_window1:
            return b & 0x0F
        return b >> 4

    def _span(
        self, vdc1: Sequence[int], vdc2: Sequence[int], x0: int, x1: int, div: int
    ) -> list[int]:
        dots = len(vdc1)
        edge1 = self.window_edge(self._shadow_window[0], div, dots)
        edge2 = self.window_edge(self._shadow_window[1], div, dots)
        cuts = sorted({x0, x1, *(e for e in (edge1, edge2) if x0 < e < x1)})
        out: list[int] = []
        for lo, hi in pairwise(cuts):
            cfg = self.region_config(lo < edge1, lo < edge2)
            out += self._mix_run(vdc1[lo:hi], vdc2[lo:hi], cfg)
        return out

    def _mix_run(self, a: Sequence[int], b: Sequence[int], cfg: int) -> list[int]:
        """One window area: `cfg` bit 0 enables VDC 1, bit 1 VDC 2, bits 3-2 the priority code."""
        enable1, enable2, code = cfg & 1, cfg & 2, (cfg >> 2) & 3
        if not enable1 and not enable2:
            # [hw: sgxtech] both layers off: colour 0 of the VCE table for every pixel, overscan too
            return [0] * len(a)
        if not enable2:
            return list(a)
        if not enable1:
            return list(b)
        if code in (1, 2) and self.PRIORITY_LABELS == "sgxtech":
            code = 3 - code
        if code == 1:
            # VDC 2 sprites in front of the VDC 1 background, behind VDC 1 sprites
            return [
                q if (q & SPRITE and not p & SPRITE and q & COLOUR) else (p if p & COLOUR else q)
                for p, q in zip(a, b, strict=True)
            ]
        if code == 2:
            # VDC 1 sprites behind the VDC 2 background (they stay in front of VDC 2 sprites)
            return [
                q if (p & SPRITE and not q & SPRITE and q & COLOUR) else (p if p & COLOUR else q)
                for p, q in zip(a, b, strict=True)
            ]
        # 00b and 11b: VDC 1 over VDC 2 wherever VDC 1 is opaque
        return [p if p & COLOUR else q for p, q in zip(a, b, strict=True)]


class VideoPage:
    """The video chip area, `$FF:0000-03FF` (four 256-byte pages): what the VPC decodes.

    Native mode [hw: sgxtech, "HuC6280 memory map"], a 32-byte block repeated through the 1 KiB:

        $00-$03 VDC 1   $04-$07 VDC 1 (mirror)   $08-$0F VPC   $10-$13 VDC 2
        $14-$17 VDC 2 (mirror)   $18-$1F unused, reads $FF

    PC Engine compatibility mode (the switch on the back): VDC 1 alone, mirrored every 4 bytes, as
    on a PC Engine, for games that use those mirrors. `store_immediate()` says whether the CPU's
    current write is an `ST0`/`ST1`/`ST2` (the VPC sees the instruction, not the address).
    """

    #: U-SGX4: whether `ST0`-`ST2` still follow `$0E` bit 0 with the switch in compatibility mode.
    #: `$0E` cannot be written in that mode (it is a VDC 1 mirror), so the bit is only ever left
    #: over from native mode; nothing documents it. Default: no steering in compatibility mode.
    ST_STEERS_IN_COMPAT = False

    def __init__(self, vdc1, vdc2, vpc: Vpc, *, store_immediate=lambda: False, compat=False):
        self.vdc1, self.vdc2, self.vpc = vdc1, vdc2, vpc
        self.store_immediate = store_immediate
        self.compat = compat

    def read(self, address: int, mclk: int) -> int:
        if self.compat:
            return self.vdc1.read(address & 3, mclk)
        offset = address & 0x1F
        if offset < 0x08:
            return self.vdc1.read(offset & 3, mclk)
        if offset < 0x10:
            return self.vpc.read(offset)
        if offset < 0x18:
            return self.vdc2.read(offset & 3, mclk)
        return 0xFF

    def write(self, address: int, value: int, mclk: int) -> None:
        steered = self.vpc.st_to_vdc2 and (self.ST_STEERS_IN_COMPAT or not self.compat)
        if steered and self.store_immediate():
            self.vdc2.write(address & 3, value, mclk)
            return
        if self.compat:
            self.vdc1.write(address & 3, value, mclk)
            return
        offset = address & 0x1F
        if offset < 0x08:
            self.vdc1.write(offset & 3, value, mclk)
        elif offset < 0x10:
            self.vpc.write(offset, value, mclk)
        elif offset < 0x18:
            self.vdc2.write(offset & 3, value, mclk)
