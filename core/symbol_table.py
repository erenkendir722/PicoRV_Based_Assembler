# symbol_table.py
# RV32I Assembler - Symbol Table (SYMTAB)
# Label → Adres eşlemesi, hata kontrolü


class SymbolTable:
    def __init__(self):
        self._table = {}       # {label: address}
        self._errors = []      # Hata mesajları listesi

    def add(self, label: str, address: int) -> bool:
        """
        Label'ı tabloya ekler.
        Duplicate label varsa hata kaydeder, False döner.
        Başarılıysa True döner.
        """
        if label in self._table:
            self._errors.append(
                f"HATA: '{label}' etiketi zaten tanımlı "
                f"(adres: 0x{self._table[label]:08X})"
            )
            return False
        self._table[label] = address
        return True

    def get(self, label: str) -> object:
        """
        Label'ın adresini döndürür.
        Bulunamazsa hata kaydeder, None döner.
        """
        if label not in self._table:
            self._errors.append(f"HATA: '{label}' etiketi tanımsız")
            return None
        return self._table[label]

    def contains(self, label: str) -> bool:
        """Label tabloda var mı?"""
        return label in self._table

    def get_errors(self) -> list:
        """Biriken hata mesajlarını döndürür."""
        return self._errors.copy()

    def has_errors(self) -> bool:
        """Hata var mı?"""
        return len(self._errors) > 0

    def clear_errors(self):
        """Hata listesini temizler."""
        self._errors.clear()

    def clear(self):
        """Tabloyu ve hataları tamamen temizler."""
        self._table.clear()
        self._errors.clear()

    def all_symbols(self) -> dict:
        """Tüm sembol tablosunu döndürür."""
        return self._table.copy()

    def __len__(self):
        return len(self._table)

    def __repr__(self):
        lines = ["=== Symbol Table ==="]
        if not self._table:
            lines.append("  (boş)")
        else:
            for label, addr in sorted(self._table.items(), key=lambda x: x[1]):
                lines.append(f"  {label:<20} → 0x{addr:08X}  ({addr})")
        return "\n".join(lines)


if __name__ == '__main__':
    print("=== Symbol Table Test ===\n")

    symtab = SymbolTable()

    # Normal ekleme
    symtab.add("MAIN",   0x00000000)
    symtab.add("LOOP",   0x00000008)
    symtab.add("END",    0x0000001C)
    symtab.add("DATA",   0x00000100)

    print(symtab)

    # Lookup testi
    print(f"\nLOOP adresi  → 0x{symtab.get('LOOP'):08X}")
    print(f"DATA adresi  → 0x{symtab.get('DATA'):08X}")

    # Tanımsız label testi
    print(f"\nFOO adresi   → {symtab.get('FOO')}")

    # Duplicate label testi
    print()
    symtab.add("LOOP", 0x00000020)

    # Hata listesi
    print("\n=== Hatalar ===")
    for err in symtab.get_errors():
        print(" ", err)

    print(f"\nToplam sembol: {len(symtab)}")
