# object_file.py
# RV32I Linker - Object Dosya Formatı
#
# Bir .o dosyasının yapısı (JSON):
# {
#   "name": "main",
#   "text": [[address, word, size], ...],   ← .text section
#   "data": [[address, word, size], ...],   ← .data section
#   "globals":     {"LABEL": address, ...}, ← dışa açık semboller
#   "externs":     ["LABEL", ...],          ← dışarıdan beklenen semboller
#   "relocations": [[address, "LABEL", "type"], ...],  ← çözülmemiş referanslar
#   "symtab":      {"LABEL": address, ...}  ← tüm lokal semboller
# }

import json
from dataclasses import dataclass, field


@dataclass
class ObjectFile:
    name:        str
    text:        list  # [(address, word, size)]
    data:        list  # [(address, word, size)]
    globals:     dict  # {label: address}
    externs:     list  # [label]
    relocations: list  # [(address, label, type)]
    symtab:      dict  # {label: address}

    # ─────────────────────────────────────────
    # Assembler çıktısından oluştur
    # ─────────────────────────────────────────
    @classmethod
    def from_assembler(cls, asm, name: str) -> 'ObjectFile':
        """
        Assembler nesnesinden ObjectFile üretir.
        .text ve .data ayrımı için .data direktifinin adresi referans alınır.
        """
        # .data section başlangıç adresini bul (intermediate'den)
        data_start = None
        for lc, pl in asm._intermediate:
            if pl.mnemonic and pl.mnemonic.upper() == '.DATA':
                data_start = lc
                break

        text_section = []
        data_section = []
        for addr, word, size in asm.object_code:
            if data_start is not None and addr >= data_start:
                data_section.append([addr, word, size])
            else:
                text_section.append([addr, word, size])

        return cls(
            name        = name,
            text        = text_section,
            data        = data_section,
            globals     = dict(asm.globals),
            externs     = list(asm.externs),
            relocations = [[a, lbl, t] for a, lbl, t in asm.relocations],
            symtab      = asm.symtab.all_symbols(),
        )

    # ─────────────────────────────────────────
    # Dosyaya yaz / dosyadan oku
    # ─────────────────────────────────────────
    def save(self, path: str):
        """ObjectFile'ı JSON formatında .o dosyasına yazar."""
        data = {
            'name':        self.name,
            'text':        self.text,
            'data':        self.data,
            'globals':     self.globals,
            'externs':     self.externs,
            'relocations': self.relocations,
            'symtab':      self.symtab,
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> 'ObjectFile':
        """JSON .o dosyasından ObjectFile yükler."""
        with open(path, 'r', encoding='utf-8') as f:
            d = json.load(f)
        return cls(
            name        = d['name'],
            text        = d['text'],
            data        = d['data'],
            globals     = d['globals'],
            externs     = d['externs'],
            relocations = d['relocations'],
            symtab      = d['symtab'],
        )

    # ─────────────────────────────────────────
    # Object record (H/D/T/M/E formatı)
    # ─────────────────────────────────────────
    def get_object_record(self) -> str:
        """
        SIC/XE benzeri object record formatı:
          H — Header
          D — Define (global semboller)
          R — Refer  (extern semboller)
          T — Text   (.text section makine kodu)
          M — Modification (relocation kayıtları)
          E — End
        """
        lines = []
        name = self.name[:6].upper()

        all_words = self.text + self.data
        if not all_words:
            return f"H{name:<6}000000000000\nE000000"

        start  = all_words[0][0]
        last_a, _, last_s = all_words[-1]
        length = (last_a + last_s) - start

        # H kaydı
        lines.append(f"H{name:<6}{start:06X}{length:06X}")

        # D kaydı — global semboller
        if self.globals:
            d_parts = ""
            for sym, addr in self.globals.items():
                addr_val = addr if addr is not None else 0
                d_parts += f"{sym:<6}{addr_val:06X}"
            lines.append(f"D{d_parts}")

        # R kaydı — extern semboller
        if self.externs:
            r_parts = "".join(f"{s:<6}" for s in self.externs)
            lines.append(f"R{r_parts}")

        # T kayıtları — her section için ayrı blok
        for section_words in (self.text, self.data):
            if not section_words:
                continue
            i = 0
            while i < len(section_words):
                rec_start  = section_words[i][0]
                next_addr  = rec_start
                hex_bytes  = ""
                while i < len(section_words) and len(hex_bytes) < 56:
                    addr, val, size = section_words[i]
                    if addr != next_addr:
                        break
                    hex_bytes += f"{val:0{size * 2}X}"
                    next_addr  = addr + size
                    i += 1
                byte_count = len(hex_bytes) // 2
                lines.append(f"T{rec_start:06X}{byte_count:02X}{hex_bytes}")

        # M kayıtları — relocation
        for addr, label, rtype in self.relocations:
            lines.append(f"M{addr:06X}05+{label:<6}")

        # E kaydı
        entry = self.globals.get(name, start)
        if entry is None:
            entry = start
        lines.append(f"E{entry:06X}")

        return "\n".join(lines)

    def __repr__(self):
        return (f"ObjectFile({self.name!r}, "
                f"text={len(self.text)} words, "
                f"data={len(self.data)} words, "
                f"globals={list(self.globals)}, "
                f"externs={self.externs}, "
                f"relocs={len(self.relocations)})")
