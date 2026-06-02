"""
build_tests.py — Test programlarini derle + linkle, Loader icin ciktilar uret.

Toolchain zinciri (Proje 1 + Proje 2 altyapisi kullanilir):
    .asm  --Assembler-->  ObjectFile  --Linker-->  .bin / .words.hex / .lst

Uretilen ciktilar (loader/build/ altina):
    <ad>.bin        : duz little-endian ikili program imaji (host'un gonderdigi)
    <ad>.words.hex  : her satirda bir 32-bit word (testbench $readmemh + insan okur)
    <ad>.lst        : adres | hex | kaynak listing'i

Kullanim:
    python build_tests.py            # tum testleri derle
    python build_tests.py test1_math # tek testi derle
"""
import sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))   # PicoRV_Based_Assembler
sys.path.insert(0, ROOT)

from core.assembler import Assembler
from core.object_file import ObjectFile
from core.linker import Linker

TESTS_DIR = os.path.join(HERE, "..", "tests")
BUILD_DIR = os.path.join(HERE, "..", "build")

# Loader programi text_base=0 adresinden yukler (CPU reset vektoru 0x0).
TEXT_BASE = 0x00000000
DATA_BASE = 0x00000000   # tek segment: data text'in hemen ardina yerlesir


def build_one(name: str) -> bool:
    src_path = os.path.join(TESTS_DIR, f"{name}.asm")
    if not os.path.exists(src_path):
        print(f"  HATA: kaynak bulunamadi: {src_path}")
        return False

    with open(src_path, encoding="utf-8") as f:
        src = f.read()

    # ── Assemble ───────────────────────────────────────────────────────
    asm = Assembler()
    if not asm.assemble(src, prog_name=name.upper()):
        for e in asm.errors:
            print(f"  DERLEME HATA [{name}]: {e}")
        return False

    obj = ObjectFile.from_assembler(asm, name.upper())

    # ── Link (tek modul) ───────────────────────────────────────────────
    linker = Linker(text_base=TEXT_BASE, data_base=DATA_BASE)
    if not linker.link([obj]):
        for e in linker.errors:
            print(f"  LINKER HATA [{name}]: {e}")
        return False

    os.makedirs(BUILD_DIR, exist_ok=True)
    words = len(linker.linked_code)

    # ── .bin ───────────────────────────────────────────────────────────
    bin_path = os.path.join(BUILD_DIR, f"{name}.bin")
    with open(bin_path, "wb") as f:
        f.write(linker.get_bin_output(base_addr=TEXT_BASE))

    # ── .words.hex ─────────────────────────────────────────────────────
    hex_path = os.path.join(BUILD_DIR, f"{name}.words.hex")
    with open(hex_path, "w", encoding="utf-8") as f:
        f.write(linker.get_words_hex(base_addr=TEXT_BASE) + "\n")

    # ── .lst ───────────────────────────────────────────────────────────
    lst_path = os.path.join(BUILD_DIR, f"{name}.lst")
    with open(lst_path, "w", encoding="utf-8") as f:
        f.write(linker.get_listing([obj], [asm]))

    size = os.path.getsize(bin_path)
    print(f"  {name:<12} OK  {words:>3} word  ({size} byte)  -> {name}.bin / .words.hex")
    return True


def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else [
        "test1_math", "test2_loop", "test3_func"
    ]
    print("Test programlari derleniyor + linkleniyor...")
    ok = True
    for t in targets:
        ok &= build_one(t)
    if ok:
        print(f"\nTamamlandi. Ciktilar: {os.path.normpath(BUILD_DIR)}")
    else:
        print("\nBazi hedefler BASARISIZ.")
        sys.exit(1)


if __name__ == "__main__":
    main()
