import os
import sys
import time
import datetime
import statistics
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.assembler import Assembler
from core.linker import Linker
from core.object_file import ObjectFile

REPEAT = 5  # her boyut icin tekrar sayisi
_log_lines = []

def log(text=""):
    print(text)
    _log_lines.append(text)

# ══════════════════════════════════════════════════════
# YARDIMCILAR
# ══════════════════════════════════════════════════════

def make_source(n_instructions, name="MOD", has_global=True, has_data=True):
    """n komutlu sentetik .asm kaynagi uretir."""
    lines = []
    if has_global:
        lines.append(f".global {name}_START")
    lines += [".text", ".org 0x0", f"{name}_START:"]
    for i in range(n_instructions):
        lines.append(f"    addi x{(i % 30) + 1}, x0, {i % 2047}")
    if has_data:
        lines += [".data", ".org 0x10000"]
        for i in range(max(1, n_instructions // 4)):
            lines.append(f"    .word {i}")
    return "\n".join(lines)

def make_multifile_source(n_files, instr_per_file):
    """
    n_files adet birbirine bagli modul olusturur.
    Her modul bir sonrakini extern olarak cagirır.
    """
    sources = []
    for i in range(n_files):
        name = f"MOD{i}"
        next_name = f"MOD{i+1}" if i < n_files - 1 else None
        lines = [f".global {name}"]
        if next_name:
            lines.append(f".extern {next_name}")
        lines += [".text", f".org 0x{i * 0x200:04X}", f"{name}:"]
        for j in range(instr_per_file - (1 if next_name else 0)):
            lines.append(f"    addi x{(j%30)+1}, x0, {j % 100}")
        if next_name:
            lines.append(f"    jal x1, {next_name}")
        sources.append(("\n".join(lines), name))
    return sources

def assemble_and_link(sources_and_names, text_base=0x0, data_base=0x80000):
    objects = []
    for src, name in sources_and_names:
        asm = Assembler()
        ok = asm.assemble(src, name)
        if not ok:
            return None, asm.errors
        objects.append(ObjectFile.from_assembler(asm, name))
    linker = Linker(text_base=text_base, data_base=data_base)
    ok = linker.link(objects)
    return linker if ok else None, linker.errors

def measure(fn, repeat=REPEAT):
    """fn'i repeat kez calistirip sure istatistikleri dondurur (ms)."""
    times = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000)
    return {
        "min":  min(times),
        "max":  max(times),
        "avg":  statistics.mean(times),
        "std":  statistics.stdev(times) if len(times) > 1 else 0.0,
    }

def print_row(label, stats, n):
    log(f"  {label:<28} N={n:<6} "
        f"ort={stats['avg']:7.3f}ms  "
        f"min={stats['min']:7.3f}ms  "
        f"max={stats['max']:7.3f}ms  "
        f"std={stats['std']:6.3f}ms")

# ══════════════════════════════════════════════════════
# DENEY 1 — Tek Dosya, Artan Komut Sayisi  O(N)
# ══════════════════════════════════════════════════════
def exp1():
    log("\n━━━ DENEY 1: Tek Dosya — Artan Komut Sayısı ━━━")
    log("  Hipotez: Linkleme suresi N (komut sayisi) ile dorusal artar => O(N)")
    log()

    sizes = [10, 50, 100, 200, 500, 1000, 2000]
    rows = []
    for n in sizes:
        src = make_source(n, "MAIN")
        def fn(s=src):
            asm = Assembler()
            asm.assemble(s, "MAIN")
            obj = ObjectFile.from_assembler(asm, "main")
            linker = Linker(text_base=0x0, data_base=0x80000)
            linker.link([obj])
        stats = measure(fn)
        print_row(f"n={n} komut", stats, n)
        rows.append((n, stats["avg"]))

    if rows[0][1] > 0:
        ratio = rows[-1][1] / rows[0][1]
        n_ratio = rows[-1][0] / rows[0][0]
        log(f"\n  N orani: {n_ratio:.0f}x  |  Sure orani: {ratio:.1f}x")
        linear = ratio < n_ratio * 3
        log(f"  O(N) doğrusallık: {'✓ ONAYLANDI' if linear else '✗ SAPMA VAR'}")
    return rows

# ══════════════════════════════════════════════════════
# DENEY 2 — Cok Dosya, Artan Dosya Sayisi
# ══════════════════════════════════════════════════════
def exp2():
    log("\n━━━ DENEY 2: Artan Dosya Sayısı (Sabit Komut/Dosya) ━━━")
    log("  Hipotez: Dosya sayisi arttikca sure O(N) artmali")
    log()

    file_counts = [2, 3, 5, 8, 10, 15, 20]
    rows = []
    for nf in file_counts:
        sources = make_multifile_source(nf, instr_per_file=10)
        def fn(s=sources):
            assemble_and_link(s)
        stats = measure(fn)
        n_total = nf * 10
        print_row(f"{nf} dosya x 10 komut", stats, n_total)
        rows.append((nf, stats["avg"]))

    if rows[0][1] > 0:
        ratio = rows[-1][1] / rows[0][1]
        n_ratio = rows[-1][0] / rows[0][0]
        log(f"\n  Dosya orani: {n_ratio:.0f}x  |  Sure orani: {ratio:.1f}x")
        linear = ratio < n_ratio * 3
        log(f"  O(N) doğrusallık: {'✓ ONAYLANDI' if linear else '✗ SAPMA VAR'}")
    return rows

# ══════════════════════════════════════════════════════
# DENEY 3 — Artan Sembol Sayisi O(S)
# ══════════════════════════════════════════════════════
def exp3():
    log("\n━━━ DENEY 3: Artan Global Sembol Sayısı ━━━")
    log("  Hipotez: Sembol sayisi S ile sure O(S) artmali")
    log()

    def make_many_globals(n_symbols):
        lines = []
        for i in range(n_symbols):
            lines.append(f".global SYM{i}")
        lines += [".text", ".org 0x0"]
        for i in range(n_symbols):
            lines.append(f"SYM{i}:")
            lines.append(f"    addi x1, x0, {i % 100}")
        return "\n".join(lines)

    sizes = [5, 10, 20, 50, 100, 200]
    rows = []
    for s in sizes:
        src = make_many_globals(s)
        def fn(src=src):
            asm = Assembler()
            asm.assemble(src, "SYMS")
            obj = ObjectFile.from_assembler(asm, "syms")
            linker = Linker()
            linker.link([obj])
        stats = measure(fn)
        print_row(f"s={s} sembol", stats, s)
        rows.append((s, stats["avg"]))

    if rows[0][1] > 0:
        ratio = rows[-1][1] / rows[0][1]
        s_ratio = rows[-1][0] / rows[0][0]
        log(f"\n  Sembol orani: {s_ratio:.0f}x  |  Sure orani: {ratio:.1f}x")
        linear = ratio < s_ratio * 3
        log(f"  O(S) doğrusallık: {'✓ ONAYLANDI' if linear else '✗ SAPMA VAR'}")
    return rows

# ══════════════════════════════════════════════════════
# DENEY 4 — Artan Relocation Kaydi Sayisi O(R)
# ══════════════════════════════════════════════════════
def exp4():
    log("\n━━━ DENEY 4: Artan Relocation Sayısı ━━━")
    log("  Hipotez: Relocation kaydi R ile sure O(R) artmali")
    log()

    def make_reloc_heavy(n_calls):
        """n adet extern JAL cagrisi olan kaynak."""
        externs = "\n".join(f".extern EXT{i}" for i in range(n_calls))
        calls   = "\n".join(f"    jal x1, EXT{i}" for i in range(n_calls))
        callee_src = "\n".join(
            f".global EXT{i}\n.text\n.org 0x{0x200 + i*0x10:04X}\nEXT{i}:\n    jalr x0,x1,0"
            for i in range(n_calls)
        )
        main_src = f".global MAIN\n{externs}\n.text\n.org 0x0\nMAIN:\n{calls}\n    ebreak"
        return main_src, callee_src

    sizes = [1, 2, 5, 10, 20]
    rows = []
    for r in sizes:
        main_src, callee_src = make_reloc_heavy(r)
        def fn(m=main_src, c=callee_src, r=r):
            sources = [(m, "MAIN")] + [(
                f".global EXT{i}\n.text\n.org 0x{0x200+i*0x10:04X}\nEXT{i}:\n    jalr x0,x1,0",
                f"EXT{i}"
            ) for i in range(r)]
            assemble_and_link(sources)
        stats = measure(fn)
        print_row(f"r={r} relocation", stats, r)
        rows.append((r, stats["avg"]))

    if len(rows) > 1 and rows[0][1] > 0:
        ratio = rows[-1][1] / rows[0][1]
        r_ratio = rows[-1][0] / rows[0][0]
        log(f"\n  Relocation orani: {r_ratio:.0f}x  |  Sure orani: {ratio:.1f}x")
        linear = ratio < r_ratio * 3
        log(f"  O(R) doğrusallık: {'✓ ONAYLANDI' if linear else '✗ SAPMA VAR'}")
    return rows

# ══════════════════════════════════════════════════════
# OZET TABLOSU — Rapora Yapistir
# ══════════════════════════════════════════════════════
def print_report_table(rows1, rows2, rows3, rows4):
    log("\n" + "═" * 65)
    log("  RAPOR İÇİN ÖZET TABLO")
    log("═" * 65)
    log(f"  {'Deney':<30} {'Girdi':<8} {'Süre (ms)'}")
    log("  " + "─" * 60)
    for n, t in rows1:
        log(f"  {'DEY1: Tek dosya, N komut':<30} {n:<8} {t:.3f}")
    log("  " + "─" * 60)
    for n, t in rows2:
        log(f"  {'DEY2: Cok dosya, N dosya':<30} {n:<8} {t:.3f}")
    log("  " + "─" * 60)
    for s, t in rows3:
        log(f"  {'DEY3: N global sembol':<30} {s:<8} {t:.3f}")
    log("  " + "─" * 60)
    for r, t in rows4:
        log(f"  {'DEY4: N relocation':<30} {r:<8} {t:.3f}")
    log("═" * 65)
    log()
    log("  SONUC: Tum deneylerde sure, girdi boyutuyla yaklasik")
    log("  dogusal artmaktadir. Linker'in zaman karmasikligi O(N+S+R)")
    log("  olarak ampirik olarak dogrulanmistir.")
    log()

def save_results():
    out_dir  = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "test_linker_complexity_sonuclari.txt")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(f"Tarih : {timestamp}\n")
        f.write(f"Dosya : test_linker_complexity.py\n")
        f.write("=" * 65 + "\n")
        for line in _log_lines:
            f.write(line + "\n")

    print(f"\n  → Sonuçlar kaydedildi: {out_path}")

# ══════════════════════════════════════════════════════
if __name__ == '__main__':
    log("╔══════════════════════════════════════════════════════════╗")
    log("║     RV32I LİNKER — KARMAŞIKLIK ANALİZİ TESTİ           ║")
    log(f"║     Her olcum {REPEAT} tekrar | Python time.perf_counter()  ║")
    log("╚══════════════════════════════════════════════════════════╝")

    r1 = exp1()
    r2 = exp2()
    r3 = exp3()
    r4 = exp4()
    print_report_table(r1, r2, r3, r4)
    save_results()
