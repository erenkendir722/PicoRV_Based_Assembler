# morse_table.asm — Mors Alfabesi Veri Tablosu
#
# Her harf icin 1 byte encoding:
#   bit[6:4] = sembol sayisi (1-4)
#   bit[3:0] = semboller (0=nokta, 1=cizgi), MSB once
#
# Ornek: 'A' = .- = 2 sembol, 01 binary
#   bit[6:4] = 010 (2)
#   bit[3:0] = 0100 (.- = 0 1, MSB once, kalan 0)
#   toplam   = 0b01001000 = 0x48 ... ama biz daha sade tutalim:
#
# Basit encoding (her harf icin 1 .word):
#   word = (sembol_sayisi << 8) | pattern
#   pattern: bit i = i. sembol (0=nokta, 1=cizgi), bit 0 = ilk sembol
#
# A = .-   = 2, 0b10    = 0x0202
# B = -... = 4, 0b0001  = 0x0401
# C = -.-. = 4, 0b0101  = 0x0405
# ...
#
# Timing (27 MHz, birim = dit suresi = 200ms):
#   DIT  = 200 ms
#   DAH  = 600 ms (3x dit)
#   semboller arasi bosluk = 200 ms
#   harfler arasi bosluk   = 600 ms
#   kelimeler arasi bosluk = 1400 ms
# ─────────────────────────────────────────────────────────────────

.global MORSE_TABLE
.global MSG_TABLE

.data
.org 0x00008000

# Mors tablosu: A'dan Z'ye, her biri 1 word
# Format: ust byte = sembol sayisi, alt byte = pattern (bit0=ilk sembol, 0=dit 1=dah)
#
#         sayi  pattern   harf  morse
MORSE_TABLE:
    .word 0x0202    # A  .-      len=2, pat=0b10   (bit0=0=dit, bit1=1=dah)
    .word 0x0401    # B  -...    len=4, pat=0b0001
    .word 0x0405    # C  -.-.    len=4, pat=0b0101
    .word 0x0301    # D  -..     len=3, pat=0b001
    .word 0x0100    # E  .       len=1, pat=0b0
    .word 0x0404    # F  ..-.    len=4, pat=0b0100
    .word 0x0303    # G  --.     len=3, pat=0b011
    .word 0x0400    # H  ....    len=4, pat=0b0000
    .word 0x0200    # I  ..      len=2, pat=0b00
    .word 0x040E    # J  .---    len=4, pat=0b1110
    .word 0x0305    # K  -.-     len=3, pat=0b101
    .word 0x0402    # L  .-..    len=4, pat=0b0010
    .word 0x0203    # M  --      len=2, pat=0b11
    .word 0x0201    # N  -.      len=2, pat=0b01
    .word 0x0307    # O  ---     len=3, pat=0b111
    .word 0x0406    # P  .--.    len=4, pat=0b0110
    .word 0x040B    # Q  --.-    len=4, pat=0b1011
    .word 0x0302    # R  .-.     len=3, pat=0b010
    .word 0x0300    # S  ...     len=3, pat=0b000
    .word 0x0101    # T  -       len=1, pat=0b1
    .word 0x0304    # U  ..-     len=3, pat=0b100
    .word 0x0408    # V  ...-    len=4, pat=0b1000
    .word 0x0306    # W  .--     len=3, pat=0b110
    .word 0x0409    # X  -..-    len=4, pat=0b1001
    .word 0x040D    # Y  -.--    len=4, pat=0b1101
    .word 0x0403    # Z  --..    len=4, pat=0b0011

# Mesaj: "SOS" — ASCII kodlari, 0xFF ile biter
# Kodlamak istediginiz metni buraya yazin (buyuk harf, 0xFF=bitis)
MSG_TABLE:
    .word 0x53      # 'S' = 0x53
    .word 0x4F      # 'O' = 0x4F
    .word 0x53      # 'S' = 0x53
    .word 0xFF      # bitis isaretcisi
