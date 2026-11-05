"""The VPC's registers and mix against sgxtech's text (tier 2), with synthetic VDC rows.

A row value is 9 bits: bit 8 sprite, bits 7-4 palette, bits 3-0 colour (0 transparent).
"""

import pytest
from helpers import timing
from pcengine_python.machine import HSYNC_CLOCKS

from supergrafx_python.vpc import Vpc

N = 64  # dots in a synthetic row
BG1, BG2 = 0x011, 0x022  # opaque background pixels of VDC 1 and VDC 2
SP1, SP2 = 0x131, 0x142  # opaque sprite pixels
CLEAR = 0x000


def row(value, n=N):
    return [value] * n


def mix(vpc, a, b, divider=4):
    return vpc.mix(timing(divider), [a, b])


def configure(vpc, *, none=0x1, w1=0x1, w2=0x1, both=0x1):
    vpc.write(0x08, (w2 << 4) | both, 0)
    vpc.write(0x09, (none << 4) | w1, 0)


# --- registers [hw: sgxtech "Video Priority Controller"] ---------------------------------------


def test_power_up_registers_are_11_11_then_zeros():
    vpc = Vpc()
    assert [vpc.read(r) for r in range(0x08, 0x10)] == [0x11, 0x11, 0, 0, 0, 0, 0, 0]
    assert vpc.st_to_vdc2 is False


def test_registers_return_what_was_written_and_the_msbs_keep_two_bits():
    vpc = Vpc()
    for reg, value, back in (
        (0x08, 0xA5, 0xA5),
        (0x09, 0x5A, 0x5A),
        (0x0A, 0xCD, 0xCD),
        (0x0B, 0xFF, 0x03),
        (0x0C, 0x12, 0x12),
        (0x0D, 0xFE, 0x02),
    ):
        vpc.write(reg, value, 0)
        assert vpc.read(reg) == back
    assert vpc.window == [0x3CD, 0x212]


def test_0e_steers_st_but_reads_zero_and_0f_is_unused():
    vpc = Vpc()
    vpc.write(0x0E, 0xFF, 0)
    assert vpc.st_to_vdc2 is True and vpc.read(0x0E) == 0
    vpc.write(0x0E, 0xFE, 0)
    assert vpc.st_to_vdc2 is False
    vpc.write(0x0F, 0xFF, 0)
    assert vpc.read(0x0F) == 0


# --- priority and enables ----------------------------------------------------------------------


def test_default_order_vdc1_over_vdc2_where_vdc1_is_opaque():
    vpc = Vpc()
    configure(vpc, none=0x3, w1=0x3, w2=0x3, both=0x3)
    a = [BG1, CLEAR, SP1, CLEAR]
    b = [BG2, BG2, BG2, SP2]
    assert mix(vpc, a, b) == [BG1, BG2, SP1, SP2]


@pytest.mark.parametrize("code", [0x0, 0xC])
def test_codes_00_and_11_are_both_the_default_order(code):
    vpc = Vpc()
    configure(vpc, none=0x3 | code, w1=0x3, w2=0x3, both=0x3)
    a = [BG1, SP1, CLEAR, CLEAR]
    b = [SP2, BG2, SP2, BG2]
    assert mix(vpc, a, b) == [BG1, SP1, SP2, BG2]


def test_one_layer_enabled_shows_only_that_vdc_and_none_shows_colour_zero():
    a, b = [BG1, SP1, CLEAR], [BG2, SP2, BG2]
    vpc = Vpc()
    configure(vpc, none=0x1)
    assert mix(vpc, a, b) == a
    configure(vpc, none=0x2)
    assert mix(vpc, a, b) == b
    configure(vpc, none=0x0)
    assert mix(vpc, a, b) == [0, 0, 0]


def test_both_off_shows_colour_zero_in_the_overscan_too():
    vpc = Vpc()
    configure(vpc, none=0x0)
    overscan = [0x100] * 4  # the VDC's backdrop/overscan code
    assert mix(vpc, overscan, overscan) == [0, 0, 0, 0]


def test_vdc2_sprites_in_front_of_vdc1_background_behind_vdc1_sprites():
    """The detectors' code 01b (Dai Makai Mura uses it); sgxtech's text calls it 10b."""
    vpc = Vpc()
    configure(vpc, none=0x3 | 0x4)  # priority bits 3-2 = 01
    a = [BG1, BG1, SP1, CLEAR]
    b = [SP2, BG2, SP2, SP2]
    assert mix(vpc, a, b) == [SP2, BG1, SP1, SP2]


def test_vdc1_sprites_behind_vdc2_background_but_in_front_of_vdc2_sprites():
    """The detectors' code 10b; sgxtech's text calls it 01b."""
    vpc = Vpc()
    configure(vpc, none=0x3 | 0x8)  # priority bits 3-2 = 10
    a = [SP1, SP1, SP1, BG1]
    b = [BG2, SP2, CLEAR, BG2]
    # VDC1 sprite hidden by a VDC2 background pixel, kept over a VDC2 sprite or transparency
    assert mix(vpc, a, b) == [BG2, SP1, SP1, BG1]


def test_sgxtech_labels_swap_the_two_codes_and_nothing_else():
    a = [SP1, BG1, CLEAR]
    b = [BG2, SP2, SP2]
    by_detectors = Vpc()
    configure(by_detectors, none=0x3 | 0x4)
    by_text = Vpc()
    by_text.PRIORITY_LABELS = "sgxtech"
    configure(by_text, none=0x3 | 0x8)
    assert mix(by_text, a, b) == mix(by_detectors, a, b)
    # the default order is untouched by the switch
    by_text2 = Vpc()
    by_text2.PRIORITY_LABELS = "sgxtech"
    configure(by_text2, none=0x3)
    assert mix(by_text2, a, b) == [SP1, BG1, SP2]


# --- windows [hw: sgxtech "Windows"] -----------------------------------------------------------


def width_for(edge, origin=32):
    """The window register value whose right edge falls on row dot `edge` at 5.37 MHz."""
    return 0x40 + edge - origin


def test_the_four_areas_take_their_own_nibbles():
    """$08 bits 7-4 window 2 only, bits 3-0 overlap; $09 bits 7-4 no window, bits 3-0 window 1."""
    vpc = Vpc()
    # none: VDC1, window 1 only: VDC2, window 2 only: both off, overlap: VDC1 and VDC2 default
    configure(vpc, none=0x1, w1=0x2, w2=0x0, both=0x3)
    vpc.write(0x0A, width_for(60), 0)  # window 1 ends at dot 60
    vpc.write(0x0C, width_for(40), 0)  # window 2 ends at dot 40
    out = mix(vpc, row(BG1), row(BG2))
    assert out[:40] == [BG1] * 40  # both windows: the overlap nibble, default order, VDC1 opaque
    assert out[40:60] == [BG2] * 20  # window 1 only
    assert out[60:] == [BG1] * (N - 60)  # no window
    # and window 2 alone, with window 1 shorter
    vpc.write(0x0A, width_for(40), 0)
    vpc.write(0x0C, width_for(60), 0)
    out = mix(vpc, row(BG1), row(BG2))
    assert out[:40] == [BG1] * 40 and out[40:60] == [0] * 20 and out[60:] == [BG1] * (N - 60)


@pytest.mark.parametrize("width", [0x00, 0x20, 0x3F, 0x40])
def test_a_window_of_0x40_or_less_is_disabled(width):
    vpc = Vpc()
    configure(vpc, none=0x1, w1=0x2)
    vpc.write(0x0A, width & 0xFF, 0)
    assert mix(vpc, row(BG1), row(BG2)) == row(BG1)


def test_3ff_covers_the_whole_row():
    vpc = Vpc()
    configure(vpc, none=0x1, w1=0x2)
    vpc.write(0x0A, 0xFF, 0)
    vpc.write(0x0B, 0x03, 0)
    assert mix(vpc, row(BG1), row(BG2)) == row(BG2)


def test_one_pixel_steps_move_the_edge_by_one_dot():
    out = []
    for width in (0x60, 0x61, 0x62):
        vpc = Vpc()
        configure(vpc, none=0x1, w1=0x2)
        vpc.write(0x0A, width, 0)
        out.append(mix(vpc, row(BG1, 128), row(BG2, 128)).count(BG2))
    assert out == [0x20 + 32, 0x21 + 32, 0x22 + 32]  # width - 0x40 + origin


def test_the_edge_origin_follows_the_dot_clock():
    for divider, origin in ((4, 32), (3, 46), (2, 32)):
        vpc = Vpc()
        configure(vpc, none=0x1, w1=0x2)
        vpc.write(0x0A, 0x50, 0)
        assert mix(vpc, row(BG1, 128), row(BG2, 128), divider).count(BG2) == 0x10 + origin


def test_the_window_origin_is_a_class_attribute():
    class Mesen(Vpc):
        WINDOW_ORIGIN = {4: 48, 3: 48, 2: 48}  # noqa: RUF012

    vpc = Mesen()
    configure(vpc, none=0x1, w1=0x2)
    vpc.write(0x0A, 0x50, 0)
    assert mix(vpc, row(BG1, 128), row(BG2, 128)).count(BG2) == 0x10 + 48


# --- writes during the line --------------------------------------------------------------------


def test_a_register_written_mid_line_takes_effect_at_that_dot():
    vpc = Vpc()
    configure(vpc, none=0x1)
    when = HSYNC_CLOCKS + 10 * 4  # the write lands as dot 10 starts at 5 MHz
    vpc.write(0x09, 0x20, when)  # no-window nibble -> VDC 2 only
    out = mix(vpc, row(BG1), row(BG2))
    assert out[:10] == [BG1] * 10 and out[10:] == [BG2] * (N - 10)
    # and it stays: the next line starts from the new state with nothing left in the log
    assert mix(vpc, row(BG1), row(BG2)) == row(BG2)


def test_a_write_in_the_next_line_does_not_leak_into_this_one():
    vpc = Vpc()
    configure(vpc, none=0x1)
    vpc.write(0x09, 0x20, 1365 + HSYNC_CLOCKS)
    assert mix(vpc, row(BG1), row(BG2)) == row(BG1)
