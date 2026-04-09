# encoder.py
# RV32I Assembler - Encoder
# ParsedLine + SYMTAB bilgisinden 32-bit makine kodu üretir

from .opcode_table import get_instruction, get_register
from .asm_parser import parse_immediate, is_register, is_label_ref


class EncoderError(Exception):
    pass


class Encoder:

    # ─────────────────────────────────────────
    # Ana encode fonksiyonu
    # ─────────────────────────────────────────

    def encode(self, mnemonic: str, operands: list, current_pc: int, symtab: dict) -> int:
        """
        Komutu 32-bit integer olarak encode eder.
        mnemonic : "ADD", "LW" vb.
        operands : parser'dan gelen liste
        current_pc: bu komutun adresi (PC-relative için)
        symtab   : {label: address}
        """
        info = get_instruction(mnemonic)
        if info is None:
            raise EncoderError(f"Bilinmeyen komut: {mnemonic}")

        fmt = info['fmt']

        if fmt == 'R':
            return self._encode_r(info, operands)
        elif fmt == 'I':
            return self._encode_i(info, operands, current_pc, symtab)
        elif fmt == 'IS':
            return self._encode_is(info, operands)
        elif fmt == 'S':
            return self._encode_s(info, operands)
        elif fmt == 'B':
            return self._encode_b(info, operands, current_pc, symtab)
        elif fmt == 'U':
            return self._encode_u(info, operands)
        elif fmt == 'J':
            return self._encode_j(info, operands, current_pc, symtab)
        elif fmt == 'SYS':
            return self._encode_sys(info)
        else:
            raise EncoderError(f"Bilinmeyen format: {fmt}")

    # ─────────────────────────────────────────
    # R-TYPE: ADD, SUB, AND, OR, XOR, SLL, SRL, SRA, SLT, SLTU
    # Sözdizimi: ADD rd, rs1, rs2
    # ─────────────────────────────────────────
    def _encode_r(self, info: dict, operands: list) -> int:
        if len(operands) != 3:
            raise EncoderError(f"R-type 3 operand gerektirir, {len(operands)} verildi")
        rd  = self._reg(operands[0])
        rs1 = self._reg(operands[1])
        rs2 = self._reg(operands[2])
        return (info['funct7'] << 25 |
                rs2           << 20 |
                rs1           << 15 |
                info['funct3']<< 12 |
                rd            <<  7 |
                info['opcode'])

    # ─────────────────────────────────────────
    # I-TYPE: ADDI, LW, LH, LB, JALR
    # Sözdizimi:
    #   ADDI rd, rs1, imm
    #   LW   rd, offset, rs1   (parser 0(x1) → ["0","x1"] yapar)
    #   JALR rd, rs1, imm
    # ─────────────────────────────────────────
    def _encode_i(self, info: dict, operands: list, pc: int, symtab: dict) -> int:
        if len(operands) != 3:
            raise EncoderError(f"I-type 3 operand gerektirir, {len(operands)} verildi")

        rd = self._reg(operands[0])

        # Load/JALR: "rd, offset, rs1"  →  operands[1]=sayı, operands[2]=register
        # Aritmetik: "rd, rs1,   imm"   →  operands[1]=register, operands[2]=sayı/label
        if is_register(operands[1]):
            rs1 = self._reg(operands[1])
            imm = self._resolve_imm(operands[2], pc, symtab, bits=12)
        else:
            imm = self._resolve_imm(operands[1], pc, symtab, bits=12)
            rs1 = self._reg(operands[2])

        self._check_range(imm, -2048, 2047, str(imm))
        imm12 = imm & 0xFFF

        return (imm12          << 20 |
                rs1            << 15 |
                info['funct3'] << 12 |
                rd             <<  7 |
                info['opcode'])

    # ─────────────────────────────────────────
    # IS-TYPE: SLLI, SRLI, SRAI  (shift immediate)
    # Sözdizimi: SLLI rd, rs1, shamt
    # imm[11:5] = funct7, imm[4:0] = shamt (0-31)
    # ─────────────────────────────────────────
    def _encode_is(self, info: dict, operands: list) -> int:
        if len(operands) != 3:
            raise EncoderError(f"Shift-I type 3 operand gerektirir")
        rd    = self._reg(operands[0])
        rs1   = self._reg(operands[1])
        shamt = parse_immediate(operands[2])
        if shamt is None or not (0 <= shamt <= 31):
            raise EncoderError(f"Shift miktarı 0-31 arasında olmalı: {operands[2]}")

        imm12 = (info['funct7'] << 5) | shamt

        return (imm12          << 20 |
                rs1            << 15 |
                info['funct3'] << 12 |
                rd             <<  7 |
                info['opcode'])

    # ─────────────────────────────────────────
    # S-TYPE: SW, SH, SB
    # Sözdizimi: SW rs2, offset, rs1
    # (parser "sw x2, 0(x1)" → ["x2","0","x1"])
    # ─────────────────────────────────────────
    def _encode_s(self, info: dict, operands: list) -> int:
        if len(operands) != 3:
            raise EncoderError(f"S-type 3 operand gerektirir, {len(operands)} verildi")
        rs2 = self._reg(operands[0])
        rs1 = self._reg(operands[2])
        imm = parse_immediate(operands[1])
        if imm is None:
            raise EncoderError(f"Geçersiz offset: {operands[1]}")

        self._check_range(imm, -2048, 2047, operands[1])
        imm12    = imm & 0xFFF
        imm_hi   = (imm12 >> 5) & 0x7F   # [11:5]
        imm_lo   = imm12 & 0x1F           # [4:0]

        return (imm_hi         << 25 |
                rs2            << 20 |
                rs1            << 15 |
                info['funct3'] << 12 |
                imm_lo         <<  7 |
                info['opcode'])

    # ─────────────────────────────────────────
    # B-TYPE: BEQ, BNE, BLT, BGE, BLTU, BGEU
    # Sözdizimi: BEQ rs1, rs2, label
    # ─────────────────────────────────────────
    def _encode_b(self, info: dict, operands: list, pc: int, symtab: dict) -> int:
        if len(operands) != 3:
            raise EncoderError(f"B-type 3 operand gerektirir, {len(operands)} verildi")
        rs1 = self._reg(operands[0])
        rs2 = self._reg(operands[1])
        offset = self._resolve_offset(operands[2], pc, symtab)

        self._check_range(offset, -4096, 4094, operands[2])
        if offset % 2 != 0:
            raise EncoderError(f"Branch offset 2'nin katı olmalı: {offset}")

        imm = offset & 0x1FFF   # 13-bit
        imm12  = (imm >> 12) & 0x1
        imm11  = (imm >> 11) & 0x1
        imm105 = (imm >>  5) & 0x3F
        imm41  = (imm >>  1) & 0xF

        return (imm12          << 31 |
                imm105         << 25 |
                rs2            << 20 |
                rs1            << 15 |
                info['funct3'] << 12 |
                imm41          <<  8 |
                imm11          <<  7 |
                info['opcode'])

    # ─────────────────────────────────────────
    # U-TYPE: LUI, AUIPC
    # Sözdizimi: LUI rd, imm
    # imm: üst 20 bit değeri
    # ─────────────────────────────────────────
    def _encode_u(self, info: dict, operands: list) -> int:
        if len(operands) != 2:
            raise EncoderError(f"U-type 2 operand gerektirir, {len(operands)} verildi")
        rd  = self._reg(operands[0])
        imm = parse_immediate(operands[1])
        if imm is None:
            raise EncoderError(f"Geçersiz immediate: {operands[1]}")

        self._check_range(imm, 0, 0xFFFFF, operands[1])
        return (imm & 0xFFFFF) << 12 | rd << 7 | info['opcode']

    # ─────────────────────────────────────────
    # J-TYPE: JAL
    # Sözdizimi: JAL rd, label
    # ─────────────────────────────────────────
    def _encode_j(self, info: dict, operands: list, pc: int, symtab: dict) -> int:
        if len(operands) != 2:
            raise EncoderError(f"J-type 2 operand gerektirir, {len(operands)} verildi")
        rd     = self._reg(operands[0])
        offset = self._resolve_offset(operands[1], pc, symtab)

        self._check_range(offset, -1048576, 1048574, operands[1])
        if offset % 2 != 0:
            raise EncoderError(f"JAL offset 2'nin katı olmalı: {offset}")

        imm = offset & 0x1FFFFF  # 21-bit
        imm20    = (imm >> 20) & 0x1
        imm1910  = (imm >> 12) & 0xFF   # [19:12]
        imm11    = (imm >> 11) & 0x1
        imm101   = (imm >>  1) & 0x3FF  # [10:1]

        return (imm20          << 31 |
                imm101         << 21 |
                imm11          << 20 |
                imm1910        << 12 |
                rd             <<  7 |
                info['opcode'])

    # ─────────────────────────────────────────
    # SYS-TYPE: ECALL, EBREAK
    # ─────────────────────────────────────────
    def _encode_sys(self, info: dict) -> int:
        return (info['imm'] << 20 | info['opcode'])

    # ─────────────────────────────────────────
    # Yardımcı fonksiyonlar
    # ─────────────────────────────────────────

    def _reg(self, token: str) -> int:
        num = get_register(token)
        if num is None:
            raise EncoderError(f"Geçersiz register: '{token}'")
        return num

    def _resolve_imm(self, token: str, pc: int, symtab: dict, bits: int = 12) -> int:
        """Token'ı immediate değerine çözer (sayı veya label)."""
        val = parse_immediate(token)
        if val is not None:
            return val
        if token in symtab:
            return symtab[token]
        raise EncoderError(f"Çözümlenemeyen operand: '{token}'")

    def _resolve_offset(self, token: str, pc: int, symtab: dict) -> int:
        """Label veya sayıdan PC-relative offset hesaplar."""
        val = parse_immediate(token)
        if val is not None:
            return val
        if token in symtab:
            return symtab[token] - pc
        raise EncoderError(f"Tanımsız label: '{token}'")

    def _check_range(self, val: int, lo: int, hi: int, token: str):
        if not (lo <= val <= hi):
            raise EncoderError(
                f"Değer aralık dışı: {token} = {val} "
                f"(geçerli: {lo} ile {hi} arası)"
            )


# ─────────────────────────────────────────────────────
if __name__ == '__main__':
    enc = Encoder()
    symtab = {'LOOP': 0x108, 'END': 0x120}
    pc = 0x100

    tests = [
        # (mnemonic, operands, beklenen hex, açıklama)
        ('ADD',   ['x1', 'x2', 'x3'],          0x003100B3, 'R-type ADD'),
        ('SUB',   ['x1', 'x2', 'x3'],          0x403100B3, 'R-type SUB'),
        ('ADDI',  ['x1', 'x0', '10'],           0x00A00093, 'I-type ADDI'),
        ('ADDI',  ['x1', 'x1', '-1'],           0xFFF08093, 'I-type ADDI negatif'),
        ('LW',    ['x1', '0', 'x2'],            0x00012083, 'I-type LW'),
        ('SW',    ['x2', '0', 'x1'],            0x0020A023, 'S-type SW'),
        ('BEQ',   ['x1', 'x0', 'LOOP'],         None,       'B-type BEQ (offset=+8)'),
        ('JAL',   ['x0', 'END'],                None,       'J-type JAL (offset=+0x20)'),
        ('LUI',   ['x1', '0x10000'],            None,       'U-type LUI'),
        ('SLLI',  ['x1', 'x1', '2'],            0x00209093, 'IS-type SLLI'),
        ('ECALL', [],                            0x00000073, 'SYS ECALL'),
        ('EBREAK',[],                            0x00100073, 'SYS EBREAK'),
    ]

    print("=== Encoder Test ===\n")
    all_ok = True
    for mnemonic, ops, expected, desc in tests:
        try:
            result = enc.encode(mnemonic, ops, pc, symtab)
            if expected is not None:
                ok = result == expected
                status = "✓" if ok else "✗"
                if not ok:
                    all_ok = False
                print(f"{status} {desc:<25} → 0x{result:08X}  (beklenen: 0x{expected:08X})")
            else:
                print(f"  {desc:<25} → 0x{result:08X}")
        except EncoderError as e:
            all_ok = False
            print(f"✗ {desc:<25} → HATA: {e}")

    print(f"\n{'✓ Tüm testler geçti.' if all_ok else '✗ Bazı testler başarısız.'}")
