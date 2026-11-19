# SPDX-License-Identifier: MIT
"""ST0/ST1/ST2 through the real HuC6280 core: the VPC sees the instruction, not the address."""

from pcengine_python.cards import RomCard

from supergrafx_python import SuperGrafx

BANK = 0x2000


def program(code: bytes) -> RomCard:
    """A one-bank HuCard: code at $E000 (MPR7 = bank 0 at reset), reset vector $FFFE -> $E000."""
    rom = bytearray([0xEA]) * BANK
    rom[: len(code)] = code
    rom[0x1FFE:0x2000] = bytes([0x00, 0xE0])
    return RomCard(bytes(rom))


CODE = bytes(
    [
        0xA9, 0xFF,  # LDA #$FF
        0x53, 0x04,  # TAM #$04: MPR2 -> bank $FF, so $4000 is the hardware page
        0xA9, 0x01,  # LDA #1
        0x8D, 0x0E, 0x40,  # STA $400E : VPC ST steering -> VDC 2
        0x03, 0x07,  # ST0 #$07 : VDC 2 register select (BXR)
        0x13, 0x12,  # ST1 #$12
        0x23, 0x01,  # ST2 #$01  : VDC 2 BXR = $0112
        0xA9, 0x07,  # LDA #7
        0x8D, 0x00, 0x40,  # STA $4000 : VDC 1 register select, a plain store
        0x9C, 0x0E, 0x40,  # STZ $400E : steering off
        0x03, 0x08,  # ST0 #$08 : VDC 1 register select (BYR)
        0x13, 0x34,  # ST1 #$34
        0x23, 0x02,  # ST2 #$02  : VDC 1 BYR = $0234
        0xDB,  # STP
    ]
)  # fmt: skip


def test_the_core_st_instructions_follow_the_vpc_and_plain_stores_do_not():
    sg = SuperGrafx(card=program(CODE))
    system = sg.build()
    for _ in range(40):
        system.step()
    assert sg.vdc2.regs.value[0x07] == 0x0112 and sg.vdc1.regs.value[0x07] == 0
    assert sg.vdc1.regs.select == 0x08 and sg.vdc1.regs.value[0x08] == 0x0234
    assert sg.vdc2.regs.value[0x08] == 0
