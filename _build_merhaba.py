"""
MERHABA projesini derler ve program.mem üretir.
Calistir: python _build_merhaba.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from core.assembler import Assembler
from core.object_file import ObjectFile
from core.linker import Linker

SRC  = "assets/tang_nano_merhaba/main.asm"
OUT  = "assets/tang_nano_merhaba/gowin_project/program.mem"
HEX  = "assets/tang_nano_merhaba/output.hex"

with open(SRC, encoding="utf-8") as f:
    source = f.read()

asm = Assembler()
ok  = asm.assemble(source, prog_name="MERHABA")

if not ok:
    for e in asm.errors:
        print("HATA:", e)
    sys.exit(1)

obj = ObjectFile.from_assembler(asm, "MERHABA")

linker = Linker(text_base=0x00000000, data_base=0x00000400)
ok = linker.link([obj])

if not ok:
    for e in linker.errors:
        print("LINKER HATA:", e)
    sys.exit(1)

# ── output.hex ────────────────────────────────────────────────────
os.makedirs(os.path.dirname(HEX), exist_ok=True)
with open(HEX, "w") as f:
    for addr, word, _size in linker.linked_code:
        f.write(f"0x{addr:08X}:  {word:08X}\n")

print(f"output.hex yazildi ({len(linker.linked_code)} word)")

# ── program.mem ($readmemh formati) ───────────────────────────────
os.makedirs(os.path.dirname(OUT), exist_ok=True)

# Sozluge al
mem = {}
for addr, word, _size in linker.linked_code:
    word_idx = addr >> 2
    mem[word_idx] = word

if mem:
    max_idx  = max(mem)
    segments = []
    seg_start = None
    prev_idx  = None

    for idx in sorted(mem):
        if seg_start is None or idx != prev_idx + 1:
            seg_start = idx
            segments.append((seg_start, []))
        segments[-1][1].append(mem[idx])
        prev_idx = idx

    with open(OUT, "w") as f:
        for seg_base, words in segments:
            f.write(f"@{seg_base:08X}\n")
            for w in words:
                f.write(f"{w:08X}\n")

    print(f"program.mem yazildi ({sum(len(w) for _,w in segments)} word)")

# ── Sembol tablosu ────────────────────────────────────────────────
print("\nSembol tablosu:")
for name, addr in sorted(linker.global_symtab.items(), key=lambda x: x[1]):
    print(f"  {name:<16} 0x{addr:08X}")
