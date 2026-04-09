# linker_script.py
# RV32I Linker Script Parser
#
# Desteklenen format (.ld dosyası):
#
#   /* yorum */
#   # yorum
#
#   MEMORY {
#       text_base = 0x00000000;
#       data_base = 0x00010000;
#   }
#
# Tüm alanlar opsiyoneldir; eksik olanlar varsayılan değerle doldurulur.

import re


# Varsayılan değerler
DEFAULTS = {
    'text_base': 0x00000000,
    'data_base': 0x00010000,
}


class LinkerScriptError(Exception):
    pass


class LinkerScript:
    """
    .ld dosyasından text_base ve data_base adreslerini okur.

    Kullanım:
        ls = LinkerScript.from_file("memory.ld")
        linker = Linker(text_base=ls.text_base, data_base=ls.data_base)
    """

    def __init__(self, text_base: int, data_base: int):
        self.text_base = text_base
        self.data_base = data_base

    # ─────────────────────────────────────────
    # Fabrika metodları
    # ─────────────────────────────────────────
    @classmethod
    def from_file(cls, path: str) -> 'LinkerScript':
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except OSError as e:
            raise LinkerScriptError(f"Dosya okunamadı: {e}")
        return cls.from_string(content)

    @classmethod
    def from_string(cls, content: str) -> 'LinkerScript':
        content = _strip_comments(content)
        values  = _parse_assignments(content)

        text_base = _resolve(values, 'text_base', DEFAULTS['text_base'])
        data_base = _resolve(values, 'data_base', DEFAULTS['data_base'])

        if text_base == data_base:
            raise LinkerScriptError(
                f"text_base ve data_base aynı olamaz: 0x{text_base:08X}")
        if text_base % 4 or data_base % 4:
            raise LinkerScriptError("Adresler 4-byte hizalı olmalıdır")

        return cls(text_base=text_base, data_base=data_base)

    @classmethod
    def default(cls) -> 'LinkerScript':
        """Varsayılan linker script."""
        return cls(**DEFAULTS)

    # ─────────────────────────────────────────
    # Gösterim
    # ─────────────────────────────────────────
    def __repr__(self):
        return (f"LinkerScript(text_base=0x{self.text_base:08X}, "
                f"data_base=0x{self.data_base:08X})")

    def to_string(self) -> str:
        """Script içeriğini metin olarak döndürür (kaydetmek için)."""
        return (
            "/* RV32I Linker Script */\n"
            "\n"
            "MEMORY {\n"
            f"    text_base = 0x{self.text_base:08X};   /* .text section başlangıcı */\n"
            f"    data_base = 0x{self.data_base:08X};   /* .data section başlangıcı */\n"
            "}\n"
        )


# ─────────────────────────────────────────
# Modül düzeyinde yardımcılar
# ─────────────────────────────────────────

def _strip_comments(content: str) -> str:
    """/* ... */ ve # ... yorumlarını siler."""
    content = re.sub(r'/\*.*?\*/', ' ', content, flags=re.DOTALL)
    content = re.sub(r'#[^\n]*', ' ', content)
    return content


def _parse_assignments(content: str) -> dict:
    """
    'anahtar = değer;' satırlarını ayrıştırır.
    Hex (0x...), binary (0b...) ve ondalık değerleri destekler.
    """
    result = {}
    for m in re.finditer(r'(\w+)\s*=\s*([^;]+);', content):
        key = m.group(1).strip()
        raw = m.group(2).strip()
        try:
            result[key] = int(raw, 0)
        except ValueError:
            raise LinkerScriptError(f"Geçersiz değer: '{key} = {raw}'")
    return result


def _resolve(values: dict, key: str, default: int) -> int:
    return values.get(key, default)
