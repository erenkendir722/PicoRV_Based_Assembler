# parser.py
# RV32I Assembler - Parser
# Her satırı label | mnemonic | operandlar olarak ayrıştırır

import re
from opcode_table import get_instruction, get_register, is_directive, DIRECTIVES


class ParsedLine:
    """Ayrıştırılmış bir assembly satırını temsil eder."""

    def __init__(self):
        self.line_number = 0
        self.original    = ""
        self.label       = None    # "LOOP" veya None
        self.mnemonic    = None    # "ADD", ".word" vb.
        self.operands    = []      # ["x1", "x2", "5"] vb.
        self.is_comment  = False
        self.is_empty    = False
        self.error       = None

    def __repr__(self):
        return (f"Satır {self.line_number:>3}: "
                f"label={self.label!r:<12} "
                f"mnemonic={self.mnemonic!r:<10} "
                f"operands={self.operands}")


class Parser:
    def __init__(self):
        self.errors = []

    def parse_all(self, source: str) -> list:
        """
        Tüm kaynak kodunu satır satır ayrıştırır.
        ParsedLine listesi döndürür.
        """
        self.errors = []
        lines = source.splitlines()
        result = []
        for i, line in enumerate(lines, start=1):
            parsed = self._parse_line(line, i)
            result.append(parsed)
        return result

    def _parse_line(self, line: str, line_number: int) -> ParsedLine:
        pl = ParsedLine()
        pl.line_number = line_number
        pl.original    = line

        # Yorum karakterlerini temizle (# veya ;)
        clean = re.split(r'[#;]', line)[0].strip()

        if not clean:
            pl.is_empty   = True
            pl.is_comment = line.strip().startswith(('#', ';'))
            return pl

        tokens = self._tokenize(clean)
        if not tokens:
            pl.is_empty = True
            return pl

        idx = 0

        # Label kontrolü: "LOOP:" veya "LOOP :" formatı
        if tokens[idx].endswith(':'):
            pl.label = tokens[idx][:-1].strip()
            idx += 1
        elif len(tokens) > 1 and tokens[idx + 1] == ':' if idx + 1 < len(tokens) else False:
            pl.label = tokens[idx]
            idx += 2

        if idx >= len(tokens):
            # Sadece label olan satır
            return pl

        # Mnemonic
        pl.mnemonic = tokens[idx].upper()
        idx += 1

        # Operandları topla
        operand_str = ' '.join(tokens[idx:])
        pl.operands = self._parse_operands(operand_str)

        # Doğrulama
        pl.error = self._validate(pl, line_number)
        if pl.error:
            self.errors.append(pl.error)

        return pl

    def _tokenize(self, line: str) -> list:
        """
        Satırı tokenlara böler.
        "add x1, x2, x3" → ["add", "x1,", "x2,", "x3"]
        """
        return line.split()

    def _parse_operands(self, operand_str: str) -> list:
        """
        Operand stringini listeye çevirir.
        "x1, x2, 5"     → ["x1", "x2", "5"]
        "0(x2)"         → ["0", "x2"]        (load/store)
        "x1, 0(x2)"     → ["x1", "0", "x2"]  (load)
        """
        if not operand_str.strip():
            return []

        # Önce virgülle böl
        parts = [p.strip() for p in operand_str.split(',')]
        result = []

        for part in parts:
            part = part.strip()
            if not part:
                continue
            # "offset(register)" formatı → ["offset", "register"]
            m = re.match(r'^(-?\w+)\((\w+)\)$', part)
            if m:
                result.append(m.group(1))   # offset
                result.append(m.group(2))   # register
            else:
                result.append(part)

        return result

    def _validate(self, pl: ParsedLine, line_number: int) -> object:
        """
        Temel doğrulama:
        - Direktif mi geçerli mi?
        - Mnemonic OPTAB'ta var mı?
        - Label ismi geçerli mi?
        """
        mnemonic = pl.mnemonic
        if mnemonic is None:
            return None

        # Direktif kontrolü
        if mnemonic.lower() in DIRECTIVES:
            return None

        # OPTAB kontrolü
        if get_instruction(mnemonic) is None:
            return f"Satır {line_number}: Bilinmeyen komut '{mnemonic}'"

        # Label isim kontrolü (harf/rakam/_  ile başlamalı)
        if pl.label and not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', pl.label):
            return f"Satır {line_number}: Geçersiz label ismi '{pl.label}'"

        return None

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def get_errors(self) -> list:
        return self.errors.copy()


# ─────────────────────────────────────────────────────
# Yardımcı fonksiyonlar (encoder/assembler tarafından kullanılır)
# ─────────────────────────────────────────────────────

def parse_immediate(token: str) -> object:
    """
    Immediate değeri parse eder.
    "5" → 5,  "0xFF" → 255,  "-3" → -3
    """
    try:
        return int(token, 0)
    except (ValueError, TypeError):
        return None


def is_register(token: str) -> bool:
    """Token bir register ismi mi?"""
    return get_register(token) is not None


def is_label_ref(token: str) -> bool:
    """Token bir label referansı mı? (register veya sayı değil)"""
    if is_register(token):
        return False
    if parse_immediate(token) is not None:
        return False
    return bool(re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', token))


# ─────────────────────────────────────────────────────
if __name__ == '__main__':
    test_code = """\
# RV32I Test Programı
.text
.org 0x100

MAIN:   addi  x1, x0, 10     # x1 = 10
        addi  x2, x0, 0      # x2 = 0
LOOP:   add   x2, x2, x1     # x2 += x1
        addi  x1, x1, -1     # x1--
        bne   x1, x0, LOOP   # x1 != 0 ise döngü
        sw    x2, 0(x0)      # sonucu yaz
        jal   x0, END
END:    ebreak

.data
COUNT:  .word  10
MSG:    .byte  0x41
"""

    parser = Parser()
    parsed_lines = parser.parse_all(test_code)

    print("=== Parser Çıktısı ===\n")
    for pl in parsed_lines:
        if pl.is_empty or pl.is_comment:
            continue
        print(pl)
        if pl.error:
            print(f"  ⚠ {pl.error}")

    if parser.has_errors():
        print("\n=== Hatalar ===")
        for err in parser.get_errors():
            print(f"  {err}")
    else:
        print("\n✓ Hata yok.")
