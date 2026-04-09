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

    def __repr__(self):
        return (f"ObjectFile({self.name!r}, "
                f"text={len(self.text)} words, "
                f"data={len(self.data)} words, "
                f"globals={list(self.globals)}, "
                f"externs={self.externs}, "
                f"relocs={len(self.relocations)})")
