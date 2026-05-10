# main.asm — Mors Kodu Ana Program
#
# MSG_TABLE'daki mesaji surekli olarak LED ile mors kodunda yayinlar.
# Mesaj bittikten sonra 3 saniye bekler ve basa doner.
#
# Mesaji degistirmek icin: morse_table.asm icerisindeki MSG_TABLE'i duzenle.
#
# Bagimliliklari:
#   SEND_CHAR(x10)   : morse.asm — tek harf gonderir
#   SEND_WORD_SPACE  : morse.asm — kelimeler arasi bosluk
#   MSG_TABLE        : morse_table.asm — gondedilecek mesaj
#   MORSE_TABLE      : morse_table.asm — mors kodu karsiliklari
#
# Register sozlesmesi:
#   x1  (ra) = donus adresi
#   x5  (t0) = mesaj isaretcisi (MSG_TABLE uzerinde gezinen adres)
#   x10 (a0) = fonksiyon argumani
# ─────────────────────────────────────────────────────────────────

.global MAIN
.extern SEND_CHAR
.extern SEND_WORD_SPACE
.extern MSG_TABLE

.text
.org 0x00000000

MAIN:
    # Yigin isaretcisini baslat (BSRAM ust siniri)
    addi  sp, x0, 0x7F0         # sp = 0x7F0 (stack bolgesi)

MSG_LOOP:
    # MSG_TABLE adresini x5'e yukle
    # MSG_TABLE = data_base(0x400) + 26*4(MORSE_TABLE) = 0x468
    addi  x5, x0, 0x400        # x5 = 0x400 (data base)
    addi  x5, x5, 0x68         # x5 = 0x468 = &MSG_TABLE[0]

READ_CHAR:
    lw    x10, 0(x5)            # x10 = simdiki karakter
    addi  x6, x0, 0xFF          # x6 = bitis isaretcisi
    beq   x10, x6, MSG_END      # karakter == 0xFF ise mesaj bitti

    # Bosluk karakteri? (0x20 = space)
    addi  x6, x0, 0x20
    beq   x10, x6, IS_SPACE

    # Normal harf: SEND_CHAR(x10)
    addi  sp, sp, -4
    sw    x1, 0(sp)
    jal   x1, SEND_CHAR
    lw    x1, 0(sp)
    addi  sp, sp, 4

    jal   x0, NEXT_CHAR

IS_SPACE:
    addi  sp, sp, -4
    sw    x1, 0(sp)
    jal   x1, SEND_WORD_SPACE
    lw    x1, 0(sp)
    addi  sp, sp, 4

NEXT_CHAR:
    addi  x5, x5, 4             # isaretciyi bir ileri al (.word = 4 byte)
    jal   x0, READ_CHAR         # sonraki karaktere gec

MSG_END:
    # Mesaj sonu: 3000 ms bekle sonra tekrar gonder
    addi  sp, sp, -4
    sw    x1, 0(sp)

    # 3000 ms = addi ile dogrudan veremeyiz (12-bit limit = 2047)
    # 3000 ms icin DELAY_MS'i iki kez cagir: 1500 + 1500
    # Ama DELAY_MS extern degil, morse.asm'de lokal.
    # Burada basit spin-wait dongusu kullanalim:
    lui   x7, 0x1A              # x7 = yaklasik 3sn spin sayisi (27MHz)
    addi  x7, x7, 0x410
WAIT_LOOP:
    addi  x7, x7, -1
    bne   x7, x0, WAIT_LOOP

    lw    x1, 0(sp)
    addi  sp, sp, 4

    jal   x0, MSG_LOOP          # basa don, mesaji tekrar gonder
