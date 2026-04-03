# assembler.py
# RV32I Assembler - Pass 1 + Pass 2
# Kaynak kodu → Object code üretimi

from asm_parser import Parser, parse_immediate, is_label_ref
from symbol_table import SymbolTable
from encoder import Encoder, EncoderError
from opcode_table import get_instruction, DIRECTIVES


class AssemblyError(Exception):
    pass


class Assembler:

    def __init__(self):
        self.parser   = Parser()
        self.symtab   = SymbolTable()
        self.encoder  = Encoder()
        self.errors   = []
        self.warnings = []

        # Pass 1 çıktısı
        self._intermediate = []   # [(lc, parsed_line)]
        self._start_addr   = 0
        self._prog_name    = "PROG"

        # Pass 2 çıktısı
        self.object_code   = []   # [(address, machine_word_int)]
        self.listing       = []   # [(address, hex_code, source_line)]

    # ─────────────────────────────────────────
    # Ana metot: assemble(source) → başarı/hata
    # ─────────────────────────────────────────
    def assemble(self, source: str, prog_name: str = "PROG") -> bool:
        self._reset()
        self._prog_name = prog_name[:6].upper()
        lines = self.parser.parse_all(source)

        self._pass1(lines)
        if self.errors:
            return False

        self._pass2()
        return not bool(self.errors)

    # ─────────────────────────────────────────
    # PASS 1: Label'ları topla, LC hesapla
    # ─────────────────────────────────────────
    def _pass1(self, lines):
        lc = 0
        in_data = False

        for pl in lines:
            if pl.is_empty or pl.is_comment or pl.mnemonic is None:
                # Sadece label olan satır
                if pl.label and pl.mnemonic is None:
                    if not self.symtab.add(pl.label, lc):
                        self._add_error(pl.line_number, self.symtab.get_errors()[-1])
                continue

            mnemonic = pl.mnemonic.upper()

            # ── Direktifler ──
            if mnemonic == '.ORG':
                addr = self._parse_int(pl.operands, 0, pl.line_number)
                if addr is not None:
                    lc = addr
                    if pl.label:
                        if not self.symtab.add(pl.label, lc):
                            self._add_error(pl.line_number, self.symtab.get_errors()[-1])
                self._intermediate.append((lc, pl))
                continue

            if mnemonic == '.TEXT':
                in_data = False
                self._intermediate.append((lc, pl))
                continue

            if mnemonic == '.DATA':
                in_data = True
                self._intermediate.append((lc, pl))
                continue

            if mnemonic == '.END':
                if pl.label:
                    self.symtab.add(pl.label, lc)
                self._intermediate.append((lc, pl))
                break

            # Label varsa SYMTAB'a ekle
            if pl.label:
                if not self.symtab.add(pl.label, lc):
                    self._add_error(pl.line_number, self.symtab.get_errors()[-1])

            # LC artışını hesapla
            size = self._get_size(mnemonic, pl.operands, pl.line_number)
            self._intermediate.append((lc, pl))
            lc += size

    # ─────────────────────────────────────────
    # PASS 2: Makine kodunu üret
    # ─────────────────────────────────────────
    def _pass2(self):
        symtab_dict = self.symtab.all_symbols()

        for lc, pl in self._intermediate:
            if pl.is_empty or pl.is_comment or pl.mnemonic is None:
                continue

            mnemonic = pl.mnemonic.upper()

            # ── Direktifler ──
            if mnemonic in ('.TEXT', '.DATA', '.ORG', '.END'):
                self.listing.append((lc, '', pl.original.strip()))
                continue

            if mnemonic == '.WORD':
                val = self._parse_int(pl.operands, 0, pl.line_number, default=0)
                word = val & 0xFFFFFFFF
                self.object_code.append((lc, word, 4))
                self.listing.append((lc, f'{word:08X}', pl.original.strip()))
                continue

            if mnemonic == '.BYTE':
                val = self._parse_int(pl.operands, 0, pl.line_number, default=0)
                byte = val & 0xFF
                self.object_code.append((lc, byte, 1))
                self.listing.append((lc, f'{byte:02X}', pl.original.strip()))
                continue

            # ── Komutlar ──
            try:
                machine_word = self.encoder.encode(
                    mnemonic, pl.operands, lc, symtab_dict
                )
                self.object_code.append((lc, machine_word, 4))
                self.listing.append((lc, f'{machine_word:08X}', pl.original.strip()))
            except EncoderError as e:
                self._add_error(pl.line_number, str(e))
                self.listing.append((lc, 'HATA', pl.original.strip()))

    # ─────────────────────────────────────────
    # Yardımcı: komutun byte boyutu
    # ─────────────────────────────────────────
    def _get_size(self, mnemonic: str, operands: list, line_no: int) -> int:
        if mnemonic == '.WORD':
            return 4
        if mnemonic == '.BYTE':
            return 1
        if mnemonic in ('.TEXT', '.DATA', '.END', '.ORG'):
            return 0
        if get_instruction(mnemonic):
            return 4
        self._add_error(line_no, f"Bilinmeyen komut: '{mnemonic}'")
        return 0

    # ─────────────────────────────────────────
    # Yardımcı: operand'dan int değeri al
    # ─────────────────────────────────────────
    def _parse_int(self, operands: list, idx: int, line_no: int, default=None):
        if idx >= len(operands):
            self._add_error(line_no, "Eksik operand")
            return default
        val = parse_immediate(operands[idx])
        if val is None:
            self._add_error(line_no, f"Geçersiz sayı: '{operands[idx]}'")
            return default
        return val

    def _add_error(self, line_no: int, msg: str):
        self.errors.append(f"Satır {line_no}: {msg}")

    def _reset(self):
        self.parser   = Parser()
        self.symtab   = SymbolTable()
        self.errors   = []
        self.warnings = []
        self._intermediate = []
        self._start_addr   = 0
        self.object_code   = []
        self.listing       = []

    # ─────────────────────────────────────────
    # Çıktı üretimi
    # ─────────────────────────────────────────
    def get_hex_output(self) -> str:
        """Her satır bir 32-bit komut, hex formatında."""
        lines = []
        for addr, word, size in self.object_code:
            lines.append(f"0x{addr:08X}:  {word:08X}")
        return "\n".join(lines)

    def get_listing(self) -> str:
        """Assembly listing: adres | hex | kaynak"""
        lines = ["Adres      Hex Kod   Kaynak",
                 "─" * 55]
        for addr, hex_code, source in self.listing:
            lines.append(f"0x{addr:08X}  {hex_code:<10}{source}")
        return "\n".join(lines)

    def get_symtab_str(self) -> str:
        return str(self.symtab)

    def get_object_record(self) -> str:
        """H/T/E formatında object program."""
        if not self.object_code:
            return ""

        start = self.object_code[0][0]
        last_addr, _, last_size = self.object_code[-1]
        end   = last_addr + last_size
        length = end - start
        name  = self._prog_name

        lines = [f"H{name:<6}{start:06X}{length:06X}"]

        # T kayıtları (max 28 byte = 7 komut × 4 byte)
        i = 0
        oc = self.object_code
        while i < len(oc):
            rec_start = oc[i][0]
            next_addr = rec_start
            hex_bytes = ""
            while i < len(oc) and len(hex_bytes) < 56:
                addr, val, size = oc[i]
                if addr != next_addr:   # adres sürekliliği bozuldu → yeni T kaydı
                    break
                hex_bytes += f"{val:0{size * 2}X}"
                next_addr = addr + size
                i += 1
            byte_count = len(hex_bytes) // 2
            lines.append(f"T{rec_start:06X}{byte_count:02X}{hex_bytes}")

        lines.append(f"E{start:06X}")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────
if __name__ == '__main__':
    test_source = """\
# 1'den 10'a kadar toplama
.text
.org 0x0

MAIN:   addi  x1, x0, 10    # x1 = 10 (sayaç)
        addi  x2, x0, 0     # x2 = 0  (toplam)
LOOP:   add   x2, x2, x1   # toplam += sayaç
        addi  x1, x1, -1    # sayaç--
        bne   x1, x0, LOOP  # sayaç != 0 ise döngü
        sw    x2, 0(x0)     # sonucu yaz
        ebreak

.data
RESULT: .word  0
"""

    asm = Assembler()
    ok  = asm.assemble(test_source)

    print("=== Assembly Listing ===")
    print(asm.get_listing())

    print("\n=== Symbol Table ===")
    print(asm.get_symtab_str())

    print("\n=== Hex Output ===")
    print(asm.get_hex_output())

    print("\n=== Object Record (H/T/E) ===")
    print(asm.get_object_record())

    if asm.errors:
        print("\n=== HATALAR ===")
        for e in asm.errors:
            print(f"  {e}")
    else:
        print("\n✓ Assembly başarılı.")
