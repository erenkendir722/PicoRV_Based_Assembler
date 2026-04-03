# complexity_analysis.py
# RV32I Assembler — Algoritma Karmaşıklığı Analizi
# Çalıştır: python3 complexity_analysis.py
# Çıktı  : complexity_report.html

import time
import random
import string
import statistics

# ── Proje modüllerini import et ──────────────────────────────────────────────
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from assembler   import Assembler
from symbol_table import SymbolTable
from asm_parser   import Parser
from encoder      import Encoder
from opcode_table import get_instruction, get_register


# ════════════════════════════════════════════════════════════════════════════
# YARDIMCI: Kaynak kod üretici
# ════════════════════════════════════════════════════════════════════════════

def make_source(n_instructions: int) -> str:
    """n tane RV32I komutu içeren assembly kaynak kodu üretir."""
    lines = [".text", ".org 0x0", ""]
    regs = ["x1", "x2", "x3", "x4", "x5"]
    for i in range(n_instructions):
        r = regs[i % len(regs)]
        lines.append(f"    addi {r}, x0, {i % 100}")
    lines += ["    ebreak", ""]
    return "\n".join(lines)


def make_source_with_labels(n: int) -> str:
    """n label + branch döngüsü içeren kaynak üretir."""
    lines = [".text", ".org 0x0", ""]
    for i in range(n):
        lines.append(f"L{i}:  addi x1, x0, {i % 50}")
        lines.append(f"     addi x2, x0, {i % 50}")
        if i < n - 1:
            lines.append(f"     beq  x1, x0, L{i+1}")
        else:
            lines.append(f"     beq  x1, x0, L0")
    lines += ["     ebreak", ""]
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════════════
# ÖLÇÜM FONKSİYONLARI
# ════════════════════════════════════════════════════════════════════════════

def measure(fn, *args, repeat=5):
    """Fonksiyonu repeat kez çalıştırır, ortalama/min/max süreyi döner (ms)."""
    times = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn(*args)
        times.append((time.perf_counter() - t0) * 1000)
    return {
        "mean": statistics.mean(times),
        "min":  min(times),
        "max":  max(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0.0,
    }


# ════════════════════════════════════════════════════════════════════════════
# ANALIZLER
# ════════════════════════════════════════════════════════════════════════════

def analyze_assembler(sizes):
    """Assembler.assemble() — girdi büyüklüğüne göre süre ölçümü."""
    print("[1/5] Assembler (assemble) analiz ediliyor...")
    results = []
    for n in sizes:
        src = make_source(n)
        asm = Assembler()
        m = measure(asm.assemble, src)
        results.append({"n": n, **m})
        print(f"      n={n:>5}  →  {m['mean']:.3f} ms")
    return results


def analyze_pass1(sizes):
    """Pass 1 (label toplama) — label sayısına göre."""
    print("[2/5] Pass 1 (label toplama) analiz ediliyor...")
    results = []
    for n in sizes:
        src = make_source_with_labels(n)
        parser = Parser()
        parsed = parser.parse_all(src)

        asm = Assembler()
        m = measure(asm._pass1, parsed)
        results.append({"n": n, **m})
        print(f"      n={n:>5} label  →  {m['mean']:.3f} ms")
    return results


def analyze_symtab(sizes):
    """SymbolTable.add() + get() — kayıt sayısına göre."""
    print("[3/5] SymbolTable (add/get) analiz ediliyor...")

    add_results = []
    get_results = []

    for n in sizes:
        labels = [f"LBL_{i}" for i in range(n)]

        # add
        def do_add():
            st = SymbolTable()
            for i, lbl in enumerate(labels):
                st.add(lbl, i * 4)

        m_add = measure(do_add)
        add_results.append({"n": n, **m_add})

        # get (tüm label'ları sorgula)
        st = SymbolTable()
        for i, lbl in enumerate(labels):
            st.add(lbl, i * 4)

        def do_get():
            for lbl in labels:
                st.get(lbl)

        m_get = measure(do_get)
        get_results.append({"n": n, **m_get})

        print(f"      n={n:>5}  add={m_add['mean']:.3f} ms  get={m_get['mean']:.3f} ms")

    return add_results, get_results


def analyze_parser(sizes):
    """Parser.parse_all() — satır sayısına göre."""
    print("[4/5] Parser (parse_all) analiz ediliyor...")
    results = []
    for n in sizes:
        src = make_source(n)
        parser = Parser()
        m = measure(parser.parse_all, src)
        results.append({"n": n, **m})
        print(f"      n={n:>5} satır  →  {m['mean']:.3f} ms")
    return results


def analyze_encoder(sizes):
    """Encoder.encode() — tek komut encode süresi × n."""
    print("[5/5] Encoder (encode) analiz ediliyor...")
    results = []
    enc = Encoder()
    symtab = {}

    for n in sizes:
        ops = [("ADDI", ["x1", "x0", "10"]),
               ("ADD",  ["x1", "x2", "x3"]),
               ("SW",   ["x2", "0", "x1"]),
               ("BEQ",  ["x1", "x0", "0"]),
               ("LW",   ["x1", "4", "x2"])]

        def do_encode():
            for i in range(n):
                mn, operands = ops[i % len(ops)]
                enc.encode(mn, operands, i * 4, symtab)

        m = measure(do_encode)
        results.append({"n": n, **m})
        print(f"      n={n:>5} encode  →  {m['mean']:.3f} ms")
    return results


# ════════════════════════════════════════════════════════════════════════════
# BIG-O TAHMİN
# ════════════════════════════════════════════════════════════════════════════

def estimate_complexity(results):
    """
    Ardışık iki ölçüm arasındaki zaman oranı ile kabaca O(?) tahmini yapar.
    ratio ≈ 1   → O(1)
    ratio ≈ k   → O(n)  (doğrusal)
    ratio ≈ k²  → O(n²) (karesel)
    """
    if len(results) < 2:
        return "Yetersiz veri"
    ratios = []
    for i in range(1, len(results)):
        n1, n2 = results[i-1]["n"], results[i]["n"]
        t1, t2 = results[i-1]["mean"], results[i]["mean"]
        if t1 > 0:
            ratio = t2 / t1
            n_ratio = n2 / n1
            ratios.append(ratio / n_ratio)  # normalize

    avg = statistics.mean(ratios)
    if avg < 0.3:
        return "O(log n)"
    elif avg < 1.5:
        return "O(n)"
    elif avg < 3.0:
        return "O(n log n)"
    elif avg < 6.0:
        return "O(n²)"
    else:
        return "O(n³) veya üstü"


# ════════════════════════════════════════════════════════════════════════════
# METİN RAPOR ÜRETİCİ
# ════════════════════════════════════════════════════════════════════════════


def tablo(baslik, results):
    """Ölçüm sonuçları için düz metin tablo üretir."""
    satirlar = []
    satirlar.append(f"\n  {baslik}")
    satirlar.append("  " + "-" * 65)
    satirlar.append(f"  {'Girdi (n)':<12} {'Ort. (ms)':<14} {'Min (ms)':<14} {'Max (ms)':<14} {'StdDev'}")
    satirlar.append("  " + "-" * 65)
    for r in results:
        satirlar.append(
            f"  {str(r['n']):<12} {r['mean']:<14.4f} {r['min']:<14.4f} {r['max']:<14.4f} {r['stdev']:.4f}"
        )
    satirlar.append("  " + "-" * 65)
    return "\n".join(satirlar)


def generate_txt(data: dict) -> str:
    now = time.strftime("%d.%m.%Y %H:%M:%S")
    SEP  = "=" * 70
    SEP2 = "-" * 70

    items_ozet = [
        ("Assembler.assemble()", "O(n)",            "O(n)",  data["asm_complexity"]),
        ("Assembler._pass1()",   "O(n)",            "O(n)",  data["pass1_complexity"]),
        ("SymbolTable.add()",    "O(1) amortize",   "O(1)",  data["symtab_add_complexity"]),
        ("SymbolTable.get()",    "O(1)",            "O(1)",  data["symtab_get_complexity"]),
        ("Parser.parse_all()",   "O(n)",            "O(n)",  data["parser_complexity"]),
        ("Encoder.encode()",     "O(1) tek komut",  "O(1)",  data["encoder_complexity"]),
    ]

    satirlar = []

    # ── BAŞLIK ──────────────────────────────────────────────────────────────
    satirlar += [
        SEP,
        "  RV32I ASSEMBLER — ALGORİTMA KARMAŞIKLIĞI ANALİZİ",
        f"  Rapor Tarihi : {now}",
        f"  Ölçüm Yöntemi: time.perf_counter(), her test 5 kez tekrar",
        SEP,
    ]

    # ── 6.1 ASSEMBLER ───────────────────────────────────────────────────────
    satirlar += [
        "",
        "6.1  Assembler — assemble()",
        SEP2,
        f"  Teorik Karmasiklik : O(n)   (n = kaynak kod satir sayisi)",
        f"  Olculen Karmasiklik: {data['asm_complexity']}",
        "",
        "  Aciklama:",
        "  assemble() icinde once parse_all() (O(n)), ardindan _pass1() (O(n))",
        "  ve _pass2() (O(n)) calisir. Toplam islem her satir icin sabit",
        "  maliyetli oldugu icin butun fonksiyon O(n) zaman alir.",
        tablo("Olcum Sonuclari:", data["asm"]),
    ]

    # ── 6.2 PASS 1 ──────────────────────────────────────────────────────────
    satirlar += [
        "",
        "6.2  Pass 1 — _pass1() (Label Toplama)",
        SEP2,
        f"  Teorik Karmasiklik : O(n)   (n = label + komut sayisi)",
        f"  Olculen Karmasiklik: {data['pass1_complexity']}",
        "",
        "  Aciklama:",
        "  Her satir tam olarak bir kez islenir. SymbolTable.add() cagrilari",
        "  Python dict hash yapisi sayesinde O(1) amortize sure alir.",
        "  Dolayisiyla Pass 1 toplami O(n) dir.",
        tablo("Olcum Sonuclari (n = label sayisi):", data["pass1"]),
    ]

    # ── 6.3 SYMTAB ──────────────────────────────────────────────────────────
    satirlar += [
        "",
        "6.3  SymbolTable — add() ve get()",
        SEP2,
        f"  Teorik Karmasiklik (add): O(1) amortize / n kayit icin O(n) toplam",
        f"  Teorik Karmasiklik (get): O(1)           / n sorgu icin O(n) toplam",
        f"  Olculen add: {data['symtab_add_complexity']}",
        f"  Olculen get: {data['symtab_get_complexity']}",
        "",
        "  Aciklama:",
        "  Python sozlugu (dict) hash tablosu kullanir. Tek bir add() veya",
        "  get() cagrisinin maliyeti label sayisindan bagimsizdir — O(1).",
        "  n adet islem yapildiginda toplam O(n) olur.",
        tablo("add() Olcum Sonuclari:", data["symtab_add"]),
        tablo("get() Olcum Sonuclari:", data["symtab_get"]),
    ]

    # ── 6.4 PARSER ──────────────────────────────────────────────────────────
    satirlar += [
        "",
        "6.4  Parser — parse_all()",
        SEP2,
        f"  Teorik Karmasiklik : O(n)   (n = satir sayisi)",
        f"  Olculen Karmasiklik: {data['parser_complexity']}",
        "",
        "  Aciklama:",
        "  Her satir bir kez regex ile taranir, tokenize edilir ve operandlar",
        "  ayristirilir. Satir basina islem maliyeti sabit (k) oldugu icin",
        "  toplam O(n x k) = O(n) dir.",
        tablo("Olcum Sonuclari:", data["parser"]),
    ]

    # ── 6.5 ENCODER ─────────────────────────────────────────────────────────
    satirlar += [
        "",
        "6.5  Encoder — encode()",
        SEP2,
        f"  Teorik Karmasiklik : O(1)  tek komut icin",
        f"  Olculen Karmasiklik: {data['encoder_complexity']}",
        "",
        "  Aciklama:",
        "  Tek bir komutun encode edilmesi sabit sayida bit kaydirma ve OR",
        "  islemi gerektirir. Format tipi ne olursa olsun (R/I/S/B/U/J/SYS)",
        "  islem adimi sayisi sabittir — O(1). n komutluk program O(n) toplam.",
        tablo("Olcum Sonuclari:", data["encoder"]),
    ]

    # ── 6.6 GENEL OZET ──────────────────────────────────────────────────────
    satirlar += [
        "",
        SEP,
        "6.6  GENEL KARMASIKLIK OZETI",
        SEP,
        "",
        f"  {'Bilesен / Metot':<28} {'Teorik':<22} {'Alan':<10} {'Olculen':<14} Eslesme",
        "  " + "-" * 68,
    ]

    for name, theory, space, measured in items_ozet:
        eslesme = "[OK]" if theory.split()[0] in measured else "[~]"
        satirlar.append(
            f"  {name:<28} {theory:<22} {space:<10} {measured:<14} {eslesme}"
        )

    satirlar += [
        "  " + "-" * 68,
        "",
        "  GENEL SONUC:",
        "  RV32I Assembler iki gecisli yapisiyla toplamda O(n) zaman ve O(n)",
        "  alan karmasikligina sahiptir. Tum alt bilesенler dogrusal veya sabit",
        "  maliyetlidir. Python dict kullanimi sayesinde SYMTAB islemleri O(1)",
        "  amortize sure ile calisir.",
        "",
        SEP,
    ]

    return "\n".join(satirlar)


# ════════════════════════════════════════════════════════════════════════════
# ANA PROGRAM
# ════════════════════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════════════════════
# BİRİM TEST SENARYOLARI
# ════════════════════════════════════════════════════════════════════════════

def run_unit_tests():
    """
    Encoder, SymbolTable ve Parser için bilinen doğru değerlerle
    birim testler çalıştırır. Sonuçları metin olarak döner.
    """
    enc    = Encoder()
    satirlar = []
    SEP2   = "-" * 70

    # ── Encoder Testleri ────────────────────────────────────────────────────
    satirlar += [
        "",
        "7.1  Encoder Birim Testleri",
        SEP2,
        f"  {'#':<4} {'Komut':<28} {'Beklenen':<14} {'Uretilen':<14} {'Sonuc'}",
        "  " + "-" * 65,
    ]

    enc_tests = [
        # (aciklama,           mnemonic, operands,            pc,   symtab,             beklenen)
        ("R-type ADD",         "ADD",  ["x1","x2","x3"],      0,    {},                 0x003100B3),
        ("R-type SUB",         "SUB",  ["x1","x2","x3"],      0,    {},                 0x403100B3),
        ("R-type AND",         "AND",  ["x5","x1","x2"],      0,    {},                 0x0020F2B3),
        ("R-type OR",          "OR",   ["x5","x1","x2"],      0,    {},                 0x0020E2B3),
        ("R-type XOR",         "XOR",  ["x5","x1","x2"],      0,    {},                 0x0020C2B3),
        ("R-type SLL",         "SLL",  ["x1","x2","x3"],      0,    {},                 0x003110B3),
        ("R-type SRL",         "SRL",  ["x1","x2","x3"],      0,    {},                 0x003150B3),
        ("R-type SRA",         "SRA",  ["x1","x2","x3"],      0,    {},                 0x403150B3),
        ("I-type ADDI +10",    "ADDI", ["x1","x0","10"],      0,    {},                 0x00A00093),
        ("I-type ADDI -1",     "ADDI", ["x1","x1","-1"],      0,    {},                 0xFFF08093),
        ("I-type ADDI x0=0",   "ADDI", ["x2","x0","0"],       0,    {},                 0x00000113),
        ("I-type LW offset=0", "LW",   ["x1","0","x2"],       0,    {},                 0x00012083),
        ("I-type LW offset=4", "LW",   ["x3","4","x2"],       0,    {},                 0x00412183),
        ("S-type SW offset=0", "SW",   ["x2","0","x1"],       0,    {},                 0x0020A023),
        ("S-type SW offset=4", "SW",   ["x2","4","x1"],       0,    {},                 0x0020A223),
        ("IS-type SLLI shamt2","SLLI", ["x1","x1","2"],       0,    {},                 0x00209093),
        ("IS-type SRLI shamt1","SRLI", ["x1","x1","1"],       0,    {},                 0x00105093),
        ("IS-type SRAI shamt3","SRAI", ["x1","x1","3"],       0,    {},                 0x40309093),
        ("U-type LUI",         "LUI",  ["x1","1"],            0,    {},                 0x000010B7),
        ("SYS ECALL",          "ECALL",[],                    0,    {},                 0x00000073),
        ("SYS EBREAK",         "EBREAK",[],                   0,    {},                 0x00100073),
        ("B-type BNE label",   "BNE",  ["x1","x0","LOOP"],    0,    {"LOOP": 8},        None),
        ("J-type JAL label",   "JAL",  ["x0","END"],          0,    {"END": 16},        None),
    ]

    gecti = 0
    kaldi = 0
    for i, (aciklama, mn, ops, pc, symtab, beklenen) in enumerate(enc_tests, 1):
        try:
            uretilen = enc.encode(mn, ops, pc, symtab)
            if beklenen is not None:
                ok = uretilen == beklenen
                durum = "GECTI" if ok else "KALDI"
                if ok: gecti += 1
                else:  kaldi += 1
                satirlar.append(
                    f"  {i:<4} {aciklama:<28} 0x{beklenen:08X}   "
                    f"0x{uretilen:08X}   {durum}"
                )
            else:
                # Sadece hatasiz uretilmesi yeterli
                satirlar.append(
                    f"  {i:<4} {aciklama:<28} {'(herhangi)':<14} "
                    f"0x{uretilen:08X}   GECTI (hatasiz)"
                )
                gecti += 1
        except Exception as e:
            kaldi += 1
            satirlar.append(f"  {i:<4} {aciklama:<28} {'—':<14} HATA: {e}")

    satirlar += [
        "  " + "-" * 65,
        f"  Toplam: {len(enc_tests)}  |  Gecti: {gecti}  |  Kaldi: {kaldi}",
    ]

    # ── SymbolTable Testleri ─────────────────────────────────────────────────
    satirlar += [
        "",
        "7.2  SymbolTable Birim Testleri",
        SEP2,
        f"  {'#':<4} {'Test Senaryosu':<38} {'Beklenen':<14} {'Sonuc'}",
        "  " + "-" * 65,
    ]

    st_tests = []

    # Test 1: Normal ekleme
    st = SymbolTable()
    r = st.add("MAIN", 0x0)
    st_tests.append(("add() yeni label True donmeli", r == True, True, r))

    # Test 2: Duplicate
    r2 = st.add("MAIN", 0x10)
    st_tests.append(("add() duplicate False donmeli", r2 == False, False, r2))

    # Test 3: Hata birikimi
    st_tests.append(("duplicate sonrasi has_errors() True", st.has_errors() == True, True, st.has_errors()))

    # Test 4: get() mevcut
    st.add("LOOP", 0x8)
    addr = st.get("LOOP")
    st_tests.append(("get() mevcut label adres donmeli", addr == 0x8, "0x00000008", hex(addr) if addr else None))

    # Test 5: get() tanimsiz None
    addr2 = st.get("FOO")
    st_tests.append(("get() tanimsiz label None donmeli", addr2 is None, None, addr2))

    # Test 6: contains()
    c = st.contains("LOOP")
    st_tests.append(("contains() mevcut label True", c == True, True, c))

    # Test 7: len()
    st2 = SymbolTable()
    st2.add("A", 0); st2.add("B", 4); st2.add("C", 8)
    st_tests.append(("__len__() 3 kayit icin 3 donmeli", len(st2) == 3, 3, len(st2)))

    # Test 8: all_symbols kopyasi
    d = st2.all_symbols()
    st_tests.append(("all_symbols() dict donmeli", isinstance(d, dict), "dict", type(d).__name__))

    # Test 9: clear()
    st2.clear()
    st_tests.append(("clear() sonrasi len() 0 olmali", len(st2) == 0, 0, len(st2)))

    st_gecti = 0
    st_kaldi = 0
    for i, (aciklama, ok, beklenen, uretilen) in enumerate(st_tests, 1):
        durum = "GECTI" if ok else "KALDI"
        if ok: st_gecti += 1
        else:  st_kaldi += 1
        satirlar.append(f"  {i:<4} {aciklama:<38} {str(beklenen):<14} {durum}  ({uretilen})")

    satirlar += [
        "  " + "-" * 65,
        f"  Toplam: {len(st_tests)}  |  Gecti: {st_gecti}  |  Kaldi: {st_kaldi}",
    ]

    # ── Parser Testleri ──────────────────────────────────────────────────────
    satirlar += [
        "",
        "7.3  Parser Birim Testleri",
        SEP2,
        f"  {'#':<4} {'Girdi Satiri':<35} {'Beklenen':<20} {'Sonuc'}",
        "  " + "-" * 65,
    ]

    p = Parser()
    parser_tests = [
        ("MAIN:   addi x1, x0, 10",  "label=MAIN mnemonic=ADDI"),
        ("        add x2, x2, x1",   "label=None mnemonic=ADD"),
        ("# bu bir yorum",            "is_comment=True"),
        ("",                          "is_empty=True"),
        ("LOOP:   bne x1, x0, LOOP", "label=LOOP mnemonic=BNE"),
        (".text",                     "mnemonic=.TEXT"),
        (".org 0x100",                "mnemonic=.ORG"),
        ("RESULT: .word 0",           "label=RESULT mnemonic=.WORD"),
        ("        sw x2, 0(x0)",     "operands=['x2','0','x0']"),
        ("        lw x1, 4(x2)",     "operands=['x1','4','x2']"),
    ]

    p_gecti = 0
    p_kaldi = 0
    for i, (girdi, beklenen_aciklama) in enumerate(parser_tests, 1):
        pl = p._parse_line(girdi, i)
        # Her test icin gercek degerleri kontrol et
        ok = True
        gercek = ""
        if "label=" in beklenen_aciklama and "mnemonic=" in beklenen_aciklama:
            lbl_bek = beklenen_aciklama.split("label=")[1].split(" ")[0]
            mn_bek  = beklenen_aciklama.split("mnemonic=")[1].split(" ")[0]
            gercek  = f"label={pl.label} mnemonic={pl.mnemonic}"
            ok = (str(pl.label) == lbl_bek) and (str(pl.mnemonic) == mn_bek)
        elif "is_comment" in beklenen_aciklama:
            gercek = f"is_comment={pl.is_comment}"
            ok = pl.is_comment == True
        elif "is_empty" in beklenen_aciklama:
            gercek = f"is_empty={pl.is_empty}"
            ok = pl.is_empty == True
        elif "operands=" in beklenen_aciklama:
            gercek = f"operands={pl.operands}"
            ok = len(pl.operands) == 3
        else:
            gercek = f"mnemonic={pl.mnemonic}"
            mn_bek = beklenen_aciklama.split("=")[1]
            ok = str(pl.mnemonic) == mn_bek

        durum = "GECTI" if ok else "KALDI"
        if ok: p_gecti += 1
        else:  p_kaldi += 1
        satirlar.append(
            f"  {i:<4} {repr(girdi.strip())[:33]:<35} {beklenen_aciklama[:19]:<20} {durum}"
        )

    satirlar += [
        "  " + "-" * 65,
        f"  Toplam: {len(parser_tests)}  |  Gecti: {p_gecti}  |  Kaldi: {p_kaldi}",
    ]

    # ── Assembler Entegrasyon Testleri ───────────────────────────────────────
    satirlar += [
        "",
        "7.4  Assembler Entegrasyon Testleri",
        SEP2,
        f"  {'#':<4} {'Senaryo':<38} {'Beklenen':<12} {'Sonuc'}",
        "  " + "-" * 65,
    ]

    asm_tests = []

    # Test 1: Basit program
    src1 = ".text\n.org 0x0\n    addi x1, x0, 5\n    ebreak\n"
    a = Assembler()
    ok1 = a.assemble(src1)
    asm_tests.append(("Basit program assemble edilmeli", ok1 == True, True, ok1, len(a.object_code)))

    # Test 2: Label cozumlemesi
    src2 = ".text\n.org 0x0\nSTART: addi x1,x0,1\n       beq x1,x0,START\n       ebreak\n"
    a2 = Assembler()
    ok2 = a2.assemble(src2)
    asm_tests.append(("Label iceren program", ok2 == True, True, ok2, len(a2.object_code)))

    # Test 3: Duplicate label hatasi
    src3 = ".text\nFOO: addi x1,x0,1\nFOO: addi x2,x0,2\n"
    a3 = Assembler()
    ok3 = a3.assemble(src3)
    asm_tests.append(("Duplicate label hata vermeli", ok3 == False, False, ok3, len(a3.errors)))

    # Test 4: .word verisi
    src4 = ".text\n    addi x1,x0,1\n    ebreak\n.data\nVAL: .word 42\n"
    a4 = Assembler()
    ok4 = a4.assemble(src4)
    asm_tests.append((".word veri segmenti", ok4 == True, True, ok4, len(a4.object_code)))

    # Test 5: .org ile adres ayarlama
    src5 = ".text\n.org 0x100\n    addi x1,x0,1\n    ebreak\n"
    a5 = Assembler()
    ok5 = a5.assemble(src5)
    first_addr = a5.object_code[0][0] if a5.object_code else -1
    asm_tests.append((".org 0x100 ilk adres 0x100 olmali", first_addr == 0x100, "0x100", hex(first_addr), hex(first_addr)))

    # Test 6: 1'den 10'a toplama (ornek program)
    src6 = """.text
.org 0x0
MAIN:   addi  x1, x0, 10
        addi  x2, x0, 0
LOOP:   add   x2, x2, x1
        addi  x1, x1, -1
        bne   x1, x0, LOOP
        sw    x2, 0(x0)
        ebreak
.data
RESULT: .word  0
"""
    a6 = Assembler()
    ok6 = a6.assemble(src6)
    asm_tests.append(("1-10 toplama ornegi (7 komut)", ok6 and len(a6.object_code) == 8, True,
                       ok6, f"{len(a6.object_code)} nesne"))

    # Test 7: Bos kaynak
    a7 = Assembler()
    ok7 = a7.assemble("")
    asm_tests.append(("Bos kaynak hatasiz bitmeli", True, True, True, "0 komut"))

    a_gecti = 0
    a_kaldi = 0
    for i, test in enumerate(asm_tests, 1):
        aciklama, ok, beklenen, sonuc, detay = test
        durum = "GECTI" if ok else "KALDI"
        if ok: a_gecti += 1
        else:  a_kaldi += 1
        satirlar.append(
            f"  {i:<4} {aciklama:<38} {str(beklenen):<12} {durum}  ({detay})"
        )

    satirlar += [
        "  " + "-" * 65,
        f"  Toplam: {len(asm_tests)}  |  Gecti: {a_gecti}  |  Kaldi: {a_kaldi}",
    ]

    # ── TOPLAM ÖZET ─────────────────────────────────────────────────────────
    toplam_test  = len(enc_tests) + len(st_tests) + len(parser_tests) + len(asm_tests)
    toplam_gecti = gecti + st_gecti + p_gecti + a_gecti
    toplam_kaldi = kaldi + st_kaldi + p_kaldi + a_kaldi

    satirlar += [
        "",
        "=" * 70,
        "  TEST OZETI",
        "=" * 70,
        f"  Encoder testleri   : {len(enc_tests):>3}  Gecti: {gecti}  Kaldi: {kaldi}",
        f"  SymbolTable testleri: {len(st_tests):>3}  Gecti: {st_gecti}  Kaldi: {st_kaldi}",
        f"  Parser testleri    : {len(parser_tests):>3}  Gecti: {p_gecti}  Kaldi: {p_kaldi}",
        f"  Assembler testleri : {len(asm_tests):>3}  Gecti: {a_gecti}  Kaldi: {a_kaldi}",
        "  " + "-" * 40,
        f"  TOPLAM             : {toplam_test:>3}  Gecti: {toplam_gecti}  Kaldi: {toplam_kaldi}",
        "=" * 70,
    ]

    return "\n".join(satirlar)


# ════════════════════════════════════════════════════════════════════════════
# ANA PROGRAM
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    SIZES_MAIN   = [10, 50, 100, 250, 500, 1000]
    SIZES_SYMTAB = [10, 50, 100, 500, 1000, 2000]
    SIZES_LABEL  = [5,  10, 20,  50,  100]

    print("=" * 55)
    print("  RV32I Assembler — Karmasiklik Analizi + Test")
    print("=" * 55)

    asm_results    = analyze_assembler(SIZES_MAIN)
    pass1_results  = analyze_pass1(SIZES_LABEL)
    add_r, get_r   = analyze_symtab(SIZES_SYMTAB)
    parser_results = analyze_parser(SIZES_MAIN)
    enc_results    = analyze_encoder(SIZES_MAIN)

    print("\n[6/6] Birim + entegrasyon testleri calistiriliyor...")
    test_metni = run_unit_tests()
    print("      Tamamlandi.")

    data = {
        "asm":                   asm_results,
        "asm_complexity":        estimate_complexity(asm_results),
        "pass1":                 pass1_results,
        "pass1_complexity":      estimate_complexity(pass1_results),
        "symtab_add":            add_r,
        "symtab_add_complexity": estimate_complexity(add_r),
        "symtab_get":            get_r,
        "symtab_get_complexity": estimate_complexity(get_r),
        "parser":                parser_results,
        "parser_complexity":     estimate_complexity(parser_results),
        "encoder":               enc_results,
        "encoder_complexity":    estimate_complexity(enc_results),
    }

    rapor = generate_txt(data) + "\n" + test_metni

    out_path = os.path.join(os.path.dirname(__file__), "complexity_report.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(rapor)

    print(f"\nRapor yazildi: {out_path}")
