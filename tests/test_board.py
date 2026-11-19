# SPDX-License-Identifier: MIT
"""The SuperGrafx through the base board's sockets: decode, RAM, IRQ1, ST steering."""

from helpers import VIDEO, PublicOpcodeCpu, ScriptedCpu, standard_display, vdc_reg
from pcengine_python.machine import LINE_CLOCKS

from supergrafx_python import SuperGrafx

VDC1, VPC, VDC2 = VIDEO, VIDEO + 0x08, VIDEO + 0x10


def machine(**kwargs):
    sg = SuperGrafx(**kwargs)
    return sg, ScriptedCpu(sg.board)


# --- the decode [hw: sgxtech "HuC6280 memory map"] ---------------------------------------------


def test_native_decode_maps_two_vdcs_and_the_vpc_in_a_32_byte_block():
    sg, cpu = machine()
    cpu.write(VDC1, 0x07)  # VDC 1 register select
    cpu.write(VDC2, 0x09)  # VDC 2 register select
    assert sg.vdc1.regs.select == 0x07 and sg.vdc2.regs.select == 0x09
    cpu.write(VIDEO + 0x04, 0x0A)  # $04-$07: VDC 1 mirror
    cpu.write(VIDEO + 0x14, 0x0B)  # $14-$17: VDC 2 mirror
    assert sg.vdc1.regs.select == 0x0A and sg.vdc2.regs.select == 0x0B
    cpu.write(VPC + 0x0, 0x5A)
    assert cpu.read(VPC + 0x0) == 0x5A and sg.vpc.priority[0] == 0x5A


def test_the_block_repeats_every_32_bytes_through_the_1k_area():
    sg, cpu = machine()
    for k in range(32):
        cpu.write(VIDEO + 32 * k + 0x10, k & 0x1F)
        assert sg.vdc2.regs.select == k & 0x1F
    cpu.write(VIDEO + 0x3E8, 0x99)  # $3E8 = 31*32 + 8: the VPC priority register again
    assert sg.vpc.priority[0] == 0x99


def test_the_gap_18_to_1f_reads_ff_and_ignores_writes():
    sg, cpu = machine()
    for offset in range(0x18, 0x20):
        assert cpu.read(VIDEO + offset) == 0xFF
        cpu.write(VIDEO + offset, 0x00)
    assert sg.vdc1.regs.select == 0 and sg.vdc2.regs.select == 0


def test_compat_switch_decodes_vdc1_alone_mirrored_every_four_bytes():
    sg, cpu = machine(compat=True)
    for offset in (0x08, 0x10, 0x14, 0x1C, 0x3FC):
        cpu.write(VIDEO + offset, 0x06)
        assert sg.vdc1.regs.select == 0x06
        cpu.write(VIDEO + offset, 0x00)
    assert sg.vdc2.regs.select == 0 and sg.vpc.read(0x08) == 0x11
    sg.compat = False  # flipping the switch re-decodes
    cpu.write(VPC, 0x77)
    assert sg.vpc.priority[0] == 0x77


# --- RAM and the bank map ----------------------------------------------------------------------


def test_32k_of_work_ram_in_banks_f8_to_fb_without_the_8k_mirror():
    sg, cpu = machine()
    banks = (0x1F0000, 0x1F2000, 0x1F4000, 0x1F6000)
    for i, base in enumerate(banks):
        cpu.write(base + 0x123, 0x10 + i)
    assert [cpu.read(b + 0x123) for b in banks] == [0x10, 0x11, 0x12, 0x13]
    assert len(sg.board.ram.data) == 32 * 1024


def test_a_pc_engine_has_the_mirror_the_supergrafx_does_not():
    from pcengine_python.board import Board

    pce = Board()
    cpu = ScriptedCpu(pce)
    cpu.write(0x1F0123, 0x42)
    assert cpu.read(0x1F2123) == 0x42  # banks F8 and F9 are one 8 KiB


def test_unused_banks_read_ff():
    _, cpu = machine()
    # [hw: sgxtech] 80-87 and 88-F6, F7 and FC-FE return $FF on a stock machine
    for bank in (0x80, 0x87, 0x88, 0xF6, 0xF7, 0xFC, 0xFD, 0xFE):
        assert cpu.read(bank << 13) == 0xFF


# --- the second VDC ----------------------------------------------------------------------------


def test_vdc2_has_its_own_vram():
    sg, cpu = machine()
    vdc_reg(cpu, VDC2, 0x00, 0x0100)  # MAWR
    vdc_reg(cpu, VDC2, 0x02, 0xBEEF)  # VWR
    # the write is held until a CPU slot; run a few cycles so it commits
    cpu.idle(40)
    assert sg.vdc2.vram[0x0100] == 0xBEEF and sg.vdc1.vram[0x0100] == 0


def test_irq1_is_the_or_of_both_vdcs_and_each_is_acknowledged_by_its_own_status_read():
    sg, cpu = machine()
    standard_display(cpu, VDC2)  # only VDC 2 raises the vertical-blank interrupt
    for _ in range(2 * 263 * LINE_CLOCKS // 12):
        cpu.idle()
        if cpu.lines[0]:
            break
    assert cpu.lines[0] and sg.vdc2.irq1 and not sg.vdc1.irq1
    cpu.read(VDC1)  # reading VDC 1's status does not clear VDC 2's request
    assert cpu.lines[0]
    status = cpu.read(VDC2)
    assert status & 0x20 and not cpu.lines[0]  # VD, now acknowledged


def test_both_vdcs_requesting_need_both_reads():
    sg, cpu = machine()
    standard_display(cpu, VDC1)
    standard_display(cpu, VDC2)
    for _ in range(2 * 263 * LINE_CLOCKS // 12):
        cpu.idle()
        if sg.vdc1.irq1 and sg.vdc2.irq1:
            break
    assert cpu.lines[0]
    cpu.read(VDC1)
    assert cpu.lines[0]  # still VDC 2
    cpu.read(VDC2)
    assert not cpu.lines[0]


# --- ST0/ST1/ST2 [hw: sgxtech "Store Immediate Control"] ---------------------------------------


def test_st_goes_to_vdc2_only_while_0e_bit_0_is_set_and_only_for_st_instructions():
    sg, cpu = machine()
    ST0, ST1, ST2 = 0x03, 0x13, 0x23
    cpu.write(0x1FE000, 0x05, ST0)
    assert sg.vdc1.regs.select == 0x05
    cpu.write(VPC + 6, 0x01)  # $0E: ST to VDC 2
    cpu.write(0x1FE000, 0x06, ST0)
    assert sg.vdc2.regs.select == 0x06 and sg.vdc1.regs.select == 0x05
    # a plain store to the same address still reaches VDC 1 ("regular access functions normally")
    cpu.write(0x1FE000, 0x07, 0x8D)
    assert sg.vdc1.regs.select == 0x07 and sg.vdc2.regs.select == 0x06
    # data ports: ST1 and ST2 (physical $1FE002 and $1FE003)
    cpu.write(0x1FE000, 0x08, ST0)  # VDC 2 select MAWR... register 8 is BXR
    cpu.write(0x1FE002, 0x34, ST1)
    cpu.write(0x1FE003, 0x01, ST2)
    assert sg.vdc2.regs.value[0x08] == 0x0134 and sg.vdc1.regs.value[0x08] == 0
    cpu.write(VPC + 6, 0x00)
    cpu.write(0x1FE000, 0x08, ST0)
    cpu.write(0x1FE002, 0x56, ST1)
    cpu.write(0x1FE003, 0x00, ST2)
    assert sg.vdc1.regs.value[0x08] == 0x0056 and sg.vdc2.regs.value[0x08] == 0x0134


def test_st_steering_is_off_with_the_switch_in_compat_position():
    sg, cpu = machine()
    cpu.write(VPC + 6, 0x01)
    sg.compat = True
    cpu.write(0x1FE000, 0x09, 0x03)
    assert sg.vdc1.regs.select == 0x09 and sg.vdc2.regs.select == 0
    sg.page.ST_STEERS_IN_COMPAT = True  # the named switch
    cpu.write(0x1FE000, 0x0A, 0x03)
    assert sg.vdc2.regs.select == 0x0A


def test_the_machine_row_is_a_japanese_console_with_two_vdcs_and_32k():
    sg, cpu = machine()
    assert sg.board.machine.country_pc_engine is True and len(sg.board.vdcs) == 2
    assert cpu.read(0x1FE000 + 0x1000) & 0x40  # I/O port D6 = 1 (PC Engine compatible)


def test_st_steering_reads_the_public_opcode_and_falls_back_to_the_private_one():
    # A core with only `_opcode` (the pinned one) and a core with only `opcode` (newer).
    for cpu_class in (ScriptedCpu, PublicOpcodeCpu):
        sg = SuperGrafx()
        cpu = cpu_class(sg.board)
        cpu.write(VPC + 6, 0x01)
        cpu.write(0x1FE000, 0x09, 0x03)  # ST0: steered to VDC 2
        assert sg.vdc2.regs.select == 0x09 and sg.vdc1.regs.select == 0
        cpu.write(0x1FE000, 0x0A, 0x8D)  # STA: a plain store, not steered
        assert sg.vdc1.regs.select == 0x0A and sg.vdc2.regs.select == 0x09
