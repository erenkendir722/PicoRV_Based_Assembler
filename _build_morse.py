"""
tang_nano_morse: belirtilen mesaji mors koduna cevirip program.mem uretir.
Kullanim: python _build_morse.py "MESAJ BURAYA"
Ornek:    python _build_morse.py "SOS"
          python _build_morse.py "MERHABA DUNYA"
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from core.assembler import Assembler
from core.object_file import ObjectFile
from core.linker import Linker

# ── Mesaj argumani ────────────────────────────────────────────────────────────
if len(sys.argv) < 2:
    print("Kullanim: python _build_morse.py \"MESAJ\"")
    print("Ornek:    python _build_morse.py \"SOS\"")
    print("          python _build_morse.py \"MERHABA DUNYA\"")
    sys.exit(1)

message = sys.argv[1].upper().strip()

invalid = sorted({c for c in message if c not in " ABCDEFGHIJKLMNOPQRSTUVWXYZ"})
if invalid:
    print(f"HATA: Gecersiz karakter(ler): {invalid}")
    print("Sadece A-Z harfleri ve bosluk kullanilabilir.")
    sys.exit(1)

if not message.replace(" ", ""):
    print("HATA: Mesaj bos olamaz.")
    sys.exit(1)

BASE = "assets/tang_nano_morse"
OUT  = f"{BASE}/gowin_project/program.mem"
HEX  = f"{BASE}/output.hex"
TABLE_ASM = f"{BASE}/morse_table.asm"

print(f'Mesaj: "{message}"')

# ── Kaynak dosyalari ──────────────────────────────────────────────────────────
with open(f"{BASE}/main.asm", encoding="utf-8") as f:
    main_src = f.read()
with open(f"{BASE}/morse.asm", encoding="utf-8") as f:
    morse_src = f.read()

# ── Dinamik morse_table.asm icerigi ──────────────────────────────────────────
def gen_table_src(msg: str) -> str:
    msg_lines = []
    for ch in msg:
        if ch == ' ':
            msg_lines.append("    .word 0x20      # ' ' kelime boslugu")
        else:
            msg_lines.append(f"    .word 0x{ord(ch):02X}      # '{ch}'")
    msg_lines.append("    .word 0xFF      # bitis isaretcisi")

    return (
        f"# morse_table.asm — mesaj: \"{msg}\"\n"
        ".global MORSE_TABLE\n"
        ".global MSG_TABLE\n\n"
        ".data\n"
        ".org 0x00000400\n\n"
        "# Mors tablosu: A'dan Z'ye (26 harf x 4 byte = 104 byte)\n"
        "# Format: ust byte = sembol sayisi, alt byte = pattern (bit0=ilk, 0=dit 1=dah)\n"
        "MORSE_TABLE:\n"
        "    .word 0x0202    # A  .-\n"
        "    .word 0x0401    # B  -...\n"
        "    .word 0x0405    # C  -.-.\n"
        "    .word 0x0301    # D  -..\n"
        "    .word 0x0100    # E  .\n"
        "    .word 0x0404    # F  ..-.\n"
        "    .word 0x0303    # G  --.\n"
        "    .word 0x0400    # H  ....\n"
        "    .word 0x0200    # I  ..\n"
        "    .word 0x040E    # J  .---\n"
        "    .word 0x0305    # K  -.-\n"
        "    .word 0x0402    # L  .-..\n"
        "    .word 0x0203    # M  --\n"
        "    .word 0x0201    # N  -.\n"
        "    .word 0x0307    # O  ---\n"
        "    .word 0x0406    # P  .--.\n"
        "    .word 0x040B    # Q  --.-\n"
        "    .word 0x0302    # R  .-.\n"
        "    .word 0x0300    # S  ...\n"
        "    .word 0x0101    # T  -\n"
        "    .word 0x0304    # U  ..-\n"
        "    .word 0x0408    # V  ...-\n"
        "    .word 0x0306    # W  .--\n"
        "    .word 0x0409    # X  -..-\n"
        "    .word 0x040D    # Y  -.--\n"
        "    .word 0x0403    # Z  --..\n\n"
        "# Mesaj: her karakter 1 word (ASCII), 0xFF ile biter\n"
        "MSG_TABLE:\n"
        + "\n".join(msg_lines) + "\n"
    )

table_src = gen_table_src(message)

# ── Derleme ───────────────────────────────────────────────────────────────────
def do_assemble(src: str, name: str) -> ObjectFile:
    asm = Assembler()
    if not asm.assemble(src, prog_name=name):
        for e in asm.errors:
            print(f"DERLEME HATA [{name}]: {e}")
        sys.exit(1)
    return ObjectFile.from_assembler(asm, name)

print("Derleniyor...")
obj_main  = do_assemble(main_src,  "MAIN")
obj_morse = do_assemble(morse_src, "MORSE")
obj_table = do_assemble(table_src, "TABLE")

# ── Linkleme ──────────────────────────────────────────────────────────────────
linker = Linker(text_base=0x00000000, data_base=0x00000400)
if not linker.link([obj_main, obj_morse, obj_table]):
    for e in linker.errors:
        print(f"LINKER HATA: {e}")
    sys.exit(1)

total_words = len(linker.linked_code)
print(f"Linklendi: {total_words} word ({total_words * 4} byte / 2048 byte BSRAM)")

# ── Cikti: output.hex ────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(HEX), exist_ok=True)
with open(HEX, "w", encoding="utf-8") as f:
    for addr, word, _ in linker.linked_code:
        f.write(f"0x{addr:08X}:  {word:08X}\n")
print(f"Yazildi: {HEX}")

# ── Cikti: program.mem ($readmemh formati) ────────────────────────────────────
os.makedirs(os.path.dirname(OUT), exist_ok=True)

mem = {}
for addr, word, _ in linker.linked_code:
    mem[addr >> 2] = word

segments = []
prev_idx = None
for idx in sorted(mem):
    if prev_idx is None or idx != prev_idx + 1:
        segments.append((idx, []))
    segments[-1][1].append(mem[idx])
    prev_idx = idx

with open(OUT, "w", encoding="utf-8") as f:
    for seg_base, words in segments:
        f.write(f"@{seg_base:08X}\n")
        for w in words:
            f.write(f"{w:08X}\n")

print(f"Yazildi: {OUT}")

# ── morse_table.asm guncelle ──────────────────────────────────────────────────
with open(TABLE_ASM, "w", encoding="utf-8") as f:
    f.write(table_src)
print(f"Guncellendi: {TABLE_ASM}")

# ── Sembol tablosu ────────────────────────────────────────────────────────────
print("\nSembol tablosu:")
for name, addr in sorted(linker.global_symtab.items(), key=lambda x: x[1]):
    print(f"  {name:<16} 0x{addr:08X}")

print(f'\nTamamlandi! "{message}" mesaji program.mem\'e yazildi.')
print("Gowin Programmer ile gowin_project/program.mem dosyasini yukleyin.")
