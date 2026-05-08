import os
import sys
import datetime
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.assembler import Assembler
from core.linker import Linker
from core.object_file import ObjectFile

PASS = "GECTİ"
FAIL = "KALDI"
results = []
_log_lines = []

def log(text=""):
    print(text)
    _log_lines.append(text)

def test(name, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((name, status, detail))
    mark = "✓" if condition else "✗"
    log(f"  {mark} [{status}] {name}")
    if detail and not condition:
        log(f"         → {detail}")

def assemble(source, name="TEST"):
    asm = Assembler()
    ok = asm.assemble(source, name)
    return asm, ok

def link(objects, text_base=0x0, data_base=0x10000):
    linker = Linker(text_base=text_base, data_base=data_base)
    ok = linker.link(objects)
    return linker, ok

# ══════════════════════════════════════════════════════
# TEST GRUBU 1 — TEK DOSYA LINKLEME
# ══════════════════════════════════════════════════════
def group1():
    log("\n━━━ GRUP 1: Tek Dosya Linkleme ━━━")

    src = """\
.global MAIN
.text
.org 0x0
MAIN:
    addi x1, x0, 42
    ebreak
.data
.org 0x1000
VAL: .word 0
"""
    asm, ok = assemble(src, "SINGLE")
    test("Tek dosya assemble", ok, str(asm.errors))
    if not ok:
        return

    obj = ObjectFile.from_assembler(asm, "single")
    linker, ok = link([obj])
    test("Tek dosya link", ok, str(linker.errors))
    test("linked_code bos degil", len(linker.linked_code) > 0)
    test("text_base 0x0 dogru", linker.linked_code[0][0] == 0x0,
         f"ilk adres: 0x{linker.linked_code[0][0]:08X}")
    test("MAIN global_symtab'ta", "MAIN" in linker.global_symtab)
    test("MAIN adresi 0x0", linker.global_symtab.get("MAIN") == 0x0,
         f"adres: {linker.global_symtab.get('MAIN')}")

# ══════════════════════════════════════════════════════
# TEST GRUBU 2 — COKLU DOSYA + EXTERN COZUMLEME
# ══════════════════════════════════════════════════════
def group2():
    log("\n━━━ GRUP 2: Çoklu Dosya ve Extern Çözümleme ━━━")

    src_main = """\
.global MAIN
.extern FOO
.text
.org 0x0
MAIN:
    jal x1, FOO
    ebreak
"""
    src_foo = """\
.global FOO
.text
.org 0x100
FOO:
    addi x10, x0, 1
    jalr x0, x1, 0
"""
    asm_m, ok_m = assemble(src_main, "MAIN")
    asm_f, ok_f = assemble(src_foo,  "FOO")
    test("main.asm assemble", ok_m, str(asm_m.errors))
    test("foo.asm assemble",  ok_f, str(asm_f.errors))
    if not (ok_m and ok_f):
        return

    obj_m = ObjectFile.from_assembler(asm_m, "main")
    obj_f = ObjectFile.from_assembler(asm_f, "foo")

    test("main extern listesi FOO iceriyor", "FOO" in obj_m.externs)
    test("foo global listesi FOO iceriyor",  "FOO" in obj_f.globals)

    linker, ok = link([obj_m, obj_f])
    test("Linkleme basarili", ok, str(linker.errors))

    foo_addr = linker.global_symtab.get("FOO")
    test("FOO global_symtab'ta",   foo_addr is not None)
    test("FOO adresi > 0",         foo_addr is not None and foo_addr > 0,
         f"adres: {foo_addr}")

    first_word = linker.linked_code[0][1]
    opcode = first_word & 0x7F
    test("JAL opcode dogru (0x6F)", opcode == 0x6F,
         f"opcode: 0x{opcode:02X}")

# ══════════════════════════════════════════════════════
# TEST GRUBU 3 — HATA SENARYOLARI
# ══════════════════════════════════════════════════════
def group3():
    log("\n━━━ GRUP 3: Hata Senaryoları ━━━")

    src_a = ".global DUP\n.text\n.org 0x0\nDUP:\n    ebreak\n"
    src_b = ".global DUP\n.text\n.org 0x100\nDUP:\n    ebreak\n"
    asm_a, _ = assemble(src_a, "A")
    asm_b, _ = assemble(src_b, "B")
    obj_a = ObjectFile.from_assembler(asm_a, "a")
    obj_b = ObjectFile.from_assembler(asm_b, "b")
    linker, ok = link([obj_a, obj_b])
    test("Cakisan global sembol -> hata", not ok, "hata yoksa problem var")
    test("Hata mesaji 'DUP' iceriyor",
         any("DUP" in e for e in linker.errors), str(linker.errors))

    src_c = ".extern HAYALET\n.text\n.org 0x0\nSTART:\n    jal x1, HAYALET\n"
    asm_c, ok_c = assemble(src_c, "C")
    test("Cozumsuz extern -> assemble tamam", ok_c)
    if ok_c:
        obj_c = ObjectFile.from_assembler(asm_c, "c")
        linker2, ok2 = link([obj_c])
        test("Cozumsuz extern -> link hatasi", not ok2)
        test("Hata mesaji 'HAYALET' iceriyor",
             any("HAYALET" in e for e in linker2.errors), str(linker2.errors))

# ══════════════════════════════════════════════════════
# TEST GRUBU 4 — SECTION ADRES YERLESTIRME
# ══════════════════════════════════════════════════════
def group4():
    log("\n━━━ GRUP 4: Section Adres Yerleştirme ━━━")

    src = """\
.global MAIN
.text
.org 0x0
MAIN:
    addi x1, x0, 1
    addi x2, x0, 2
.data
.org 0x100
DAT: .word 0xDEAD
     .word 0xBEEF
"""
    asm, ok = assemble(src, "LAYOUT")
    test("Adres testi assemble", ok, str(asm.errors))
    if not ok:
        return

    obj = ObjectFile.from_assembler(asm, "layout")
    linker, ok = link([obj], text_base=0x1000, data_base=0x5000)
    test("Ozel base adresiyle link", ok, str(linker.errors))

    addrs = [addr for addr, _, _ in linker.linked_code]
    test("text 0x1000'den basliyor", 0x1000 in addrs,
         f"adresler: {[hex(a) for a in addrs]}")
    test("data 0x5000'den basliyor", 0x5000 in addrs,
         f"adresler: {[hex(a) for a in addrs]}")

    data_words = {addr: word for addr, word, _ in linker.linked_code
                  if addr >= 0x5000}
    test("DAT[0] = 0xDEAD", data_words.get(0x5000) == 0xDEAD,
         f"deger: 0x{data_words.get(0x5000, 0):08X}")
    test("DAT[1] = 0xBEEF", data_words.get(0x5004) == 0xBEEF,
         f"deger: 0x{data_words.get(0x5004, 0):08X}")

# ══════════════════════════════════════════════════════
# TEST GRUBU 5 — FIBONACCI ENTEGRASYON
# ══════════════════════════════════════════════════════
def group5():
    log("\n━━━ GRUP 5: Fibonacci Entegrasyon Testi ━━━")

    base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    main_path = os.path.join(base, 'assets', 'fibonacci', 'main.asm')
    math_path = os.path.join(base, 'assets', 'fibonacci', 'math.asm')

    try:
        with open(main_path) as f: src_main = f.read()
        with open(math_path) as f: src_math = f.read()
    except FileNotFoundError as e:
        log(f"  ! Dosya bulunamadi: {e}")
        return

    asm_m, ok_m = assemble(src_main, "MAIN")
    asm_f, ok_f = assemble(src_math, "MATH")
    test("fibonacci/main.asm assemble", ok_m, str(asm_m.errors))
    test("fibonacci/math.asm assemble", ok_f, str(asm_f.errors))
    if not (ok_m and ok_f):
        return

    obj_m = ObjectFile.from_assembler(asm_m, "main")
    obj_f = ObjectFile.from_assembler(asm_f, "math")
    linker, ok = link([obj_m, obj_f])
    test("Fibonacci link basarili", ok, str(linker.errors))
    test("FIB_STEP global_symtab'ta", "FIB_STEP" in linker.global_symtab)
    test("MAIN global_symtab'ta",    "MAIN"     in linker.global_symtab)
    test(".mem ciktisi bos degil",   len(linker.get_mem_output()) > 0)
    test(".hex ciktisi bos degil",   len(linker.get_hex_output()) > 0)
    test("link_map dolu",            len(linker.link_map) > 0)

    fib_addr  = linker.global_symtab.get("FIB_STEP")
    main_addr = linker.global_symtab.get("MAIN")
    test("FIB_STEP adresi MAIN'den buyuk",
         fib_addr is not None and main_addr is not None and fib_addr > main_addr,
         f"MAIN=0x{main_addr:08X} FIB_STEP=0x{fib_addr:08X}")

# ══════════════════════════════════════════════════════
# ÖZET + DOSYAYA KAYDET
# ══════════════════════════════════════════════════════
def summary():
    total  = len(results)
    passed = sum(1 for _, s, _ in results if s == PASS)
    failed = total - passed

    log("\n" + "═" * 55)
    log(f"  TOPLAM: {total}  |  GECTİ: {passed}  |  KALDI: {failed}")
    log("═" * 55)
    if failed:
        log("\n  Başarısız testler:")
        for name, status, detail in results:
            if status == FAIL:
                log(f"    ✗ {name}")
                if detail:
                    log(f"      {detail}")
    log()

def save_results():
    out_dir  = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "test_linker_sonuclari.txt")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(f"Tarih : {timestamp}\n")
        f.write(f"Dosya : test_linker.py\n")
        f.write("=" * 55 + "\n")
        for line in _log_lines:
            f.write(line + "\n")

    print(f"\n  → Sonuçlar kaydedildi: {out_path}")

if __name__ == '__main__':
    log("╔══════════════════════════════════════════════════════╗")
    log("║         RV32I LİNKER — GENEL TEST PAKETİ            ║")
    log("╚══════════════════════════════════════════════════════╝")
    group1()
    group2()
    group3()
    group4()
    group5()
    summary()
    save_results()
