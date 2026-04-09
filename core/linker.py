# linker.py
# RV32I Linker
#
# Birden fazla ObjectFile'ı alır:
#   1. .text section'larını arka arkaya yerleştirir
#   2. .data section'larını arka arkaya yerleştirir
#   3. Global sembol tablolarını birleştirir
#   4. Extern referanslarını çözer (relocation)
#   5. Tek bir yürütülebilir HEX çıktısı üretir

from .object_file import ObjectFile


class LinkerError(Exception):
    pass


class Linker:

    # Varsayılan bellek düzeni (linker script gibi)
    DEFAULT_TEXT_BASE = 0x00000000
    DEFAULT_DATA_BASE = 0x00010000

    def __init__(self, text_base: int = DEFAULT_TEXT_BASE,
                       data_base: int = DEFAULT_DATA_BASE):
        self.text_base = text_base
        self.data_base = data_base

        self.errors   = []
        self.warnings = []

        # Çıktı
        self.linked_code  = []   # [(address, word, size)] — tüm linked words
        self.global_symtab = {}  # {label: final_address}
        self.link_map      = []  # [(name, section, orig_addr, final_addr)]

    # ─────────────────────────────────────────
    # Ana metot
    # ─────────────────────────────────────────
    def link(self, object_files: list[ObjectFile]) -> bool:
        """
        ObjectFile listesini linkler.
        Başarılıysa True, hata varsa False döner.
        """
        self._reset()

        # Adım 1: Section'ları yerleştir, adres haritasını çıkar
        text_words, text_offsets = self._layout_section(
            [o.text for o in object_files],
            [o.name for o in object_files],
            self.text_base, 'text'
        )
        data_words, data_offsets = self._layout_section(
            [o.data for o in object_files],
            [o.name for o in object_files],
            self.data_base, 'data'
        )

        # Adım 2: Global sembol tablolarını yeniden adreslendirerek birleştir
        for i, obj in enumerate(object_files):
            t_off = text_offsets[i]
            d_off = data_offsets[i]

            for label, orig_addr in obj.globals.items():
                if orig_addr is None:
                    self._add_error(f"[{obj.name}] '{label}' global olarak bildirilmiş ama tanımsız")
                    continue

                # Adres hangi section'da?
                final_addr = self._relocate_addr(orig_addr, obj, t_off, d_off)

                if label in self.global_symtab:
                    self._add_error(
                        f"Çakışan global sembol '{label}': "
                        f"{obj.name} ve önceki tanım"
                    )
                else:
                    self.global_symtab[label] = final_addr

        if self.errors:
            return False

        # Adım 3: Extern bağımlılıklarını kontrol et
        for obj in object_files:
            for sym in obj.externs:
                if sym not in self.global_symtab:
                    self._add_error(f"[{obj.name}] Çözümlenemeyen extern sembol: '{sym}'")

        if self.errors:
            return False

        # Adım 4: Relocation — extern referansları düzelt
        all_words = text_words + data_words
        word_index = {addr: i for i, (addr, _, _) in enumerate(all_words)}

        reloc_offset = 0
        for i, obj in enumerate(object_files):
            t_off = text_offsets[i]
            d_off = data_offsets[i]

            for orig_addr, label, rtype in obj.relocations:
                final_sym_addr = self.global_symtab.get(label)
                if final_sym_addr is None:
                    self._add_error(f"[{obj.name}] Relocation: '{label}' çözülemedi")
                    continue

                instr_addr = self._relocate_addr(orig_addr, obj, t_off, d_off)
                idx = word_index.get(instr_addr)
                if idx is None:
                    self._add_error(f"[{obj.name}] Relocation adresi bulunamadı: 0x{instr_addr:08X}")
                    continue

                _, old_word, size = all_words[idx]
                new_word = self._patch_word(old_word, instr_addr, final_sym_addr, rtype)
                all_words[idx] = (instr_addr, new_word, size)

        if self.errors:
            return False

        self.linked_code = all_words
        return True

    # ─────────────────────────────────────────
    # Section yerleştirme
    # ─────────────────────────────────────────
    def _layout_section(self, sections, names, base_addr, section_name):
        """
        Her object dosyasının section'ını sırayla yerleştirir.
        Döndürür: (tüm_words_listesi, her_obj_için_offset_listesi)
        """
        all_words = []
        offsets   = []
        cursor    = base_addr

        for i, words in enumerate(sections):
            if not words:
                offsets.append(0)
                continue

            orig_base = words[0][0]
            offset    = cursor - orig_base
            offsets.append(offset)

            for addr, word, size in words:
                final_addr = addr + offset
                all_words.append((final_addr, word, size))
                self.link_map.append((names[i], section_name, addr, final_addr))

            last_addr, _, last_size = words[-1]
            cursor = last_addr + offset + last_size
            # 4-byte hizalama
            if cursor % 4:
                cursor += 4 - (cursor % 4)

        return all_words, offsets

    # ─────────────────────────────────────────
    # Adres yeniden hesaplama
    # ─────────────────────────────────────────
    def _relocate_addr(self, orig_addr: int, obj: ObjectFile,
                       text_offset: int, data_offset: int) -> int:
        """Orijinal adresi text mi data mi olduğuna göre kaydırır."""
        data_start = obj.data[0][0] if obj.data else None
        if data_start is not None and orig_addr >= data_start:
            return orig_addr + data_offset
        return orig_addr + text_offset

    # ─────────────────────────────────────────
    # Relocation: komut içindeki adresi güncelle
    # ─────────────────────────────────────────
    def _patch_word(self, word: int, pc: int, target: int, rtype: str) -> int:
        """
        Makine kodundaki extern referansı gerçek adresle yamar.
        rtype: 'J' | 'B' | 'I' | 'ABS'
        """
        if rtype == 'J':
            offset = (target - pc) & 0x1FFFFF
            if offset % 2 != 0:
                self._add_error(f"JAL relocation offset tek sayı: {offset}")
                return word
            imm20   = (offset >> 20) & 0x1
            imm1910 = (offset >> 12) & 0xFF
            imm11   = (offset >> 11) & 0x1
            imm101  = (offset >>  1) & 0x3FF
            imm_field = (imm20 << 19 | imm101 << 9 | imm11 << 8 | imm1910)
            return (word & 0x00000FFF) | (imm_field << 12)

        elif rtype == 'B':
            offset = (target - pc) & 0x1FFF
            if offset % 2 != 0:
                self._add_error(f"Branch relocation offset tek sayı: {offset}")
                return word
            imm12  = (offset >> 12) & 0x1
            imm11  = (offset >> 11) & 0x1
            imm105 = (offset >>  5) & 0x3F
            imm41  = (offset >>  1) & 0xF
            return ((word & 0x01FFF07F) |
                    (imm12  << 31) | (imm105 << 25) |
                    (imm41  <<  8) | (imm11  <<  7))

        elif rtype == 'I':
            imm12 = target & 0xFFF
            return (word & 0x000FFFFF) | (imm12 << 20)

        else:  # ABS
            return target & 0xFFFFFFFF

    # ─────────────────────────────────────────
    # Çıktı üretimi
    # ─────────────────────────────────────────
    def get_hex_output(self) -> str:
        """Intel HEX benzeri düz adres:değer formatı."""
        return "\n".join(f"0x{addr:08X}:  {word:08X}"
                         for addr, word, _ in self.linked_code)

    def get_mem_output(self) -> str:
        """
        Xilinx/Intel FPGA $readmemh formatı.
        Her satır bir 32-bit hex word (adres yorumu @ ile).
        """
        lines = []
        prev_addr = None
        for addr, word, size in self.linked_code:
            if size != 4:
                continue
            if prev_addr is None or addr != prev_addr + 4:
                lines.append(f"@{addr // 4:08X}")
            lines.append(f"{word:08X}")
            prev_addr = addr
        return "\n".join(lines)

    def get_link_map(self) -> str:
        """Linker map: hangi sembol hangi final adreste."""
        lines = ["Link Map",
                 "─" * 60,
                 f"  {'Modül':<12} {'Section':<8} {'Orijinal':>12} {'Final':>12}",
                 "─" * 60]
        for name, section, orig, final in self.link_map:
            lines.append(f"  {name:<12} {section:<8} 0x{orig:08X}   0x{final:08X}")
        lines += ["─" * 60, "",
                  "Global Sembol Tablosu",
                  "─" * 60]
        for label, addr in sorted(self.global_symtab.items(), key=lambda x: x[1]):
            lines.append(f"  {label:<20} → 0x{addr:08X}")
        return "\n".join(lines)

    # ─────────────────────────────────────────
    # Yardımcılar
    # ─────────────────────────────────────────
    def _add_error(self, msg: str):
        self.errors.append(msg)

    def _reset(self):
        self.errors        = []
        self.warnings      = []
        self.linked_code   = []
        self.global_symtab = {}
        self.link_map      = []
