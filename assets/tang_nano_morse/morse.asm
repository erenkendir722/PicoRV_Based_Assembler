# morse.asm — Mors Kodu LED Surucusu
#
# Dis fonksiyonlar (main.asm'den cagirilir):
#   SEND_CHAR(x10 = ASCII karakter)
#   SEND_WORD_SPACE()
#
# GPIO: 0x02000000, bit0 = LED0 (1=yanik)
#
# Register sozlesmesi:
#   x1  = return address
#   x10 = arguman
#   x11 = gecici (ic dongu sayaci)
#   x12 = morse pattern
#   x13 = sembol sayisi
#   x14 = GPIO adresi
#   x15 = gecici
# ─────────────────────────────────────────────────────────────────

.global SEND_CHAR
.global SEND_WORD_SPACE
.extern MORSE_TABLE

.text
.org 0x00000200

# ── DELAY_MS ──────────────────────────────────────────────────────
# x10 = milisaniye (max 2047)
# 27 MHz, ic dongu = 4 komut => 6750 iter = 1 ms
# 6750 = 0x1A3E, lui+addi ile: lui x11,2 (8192) addi -1442 = 6750
DELAY_MS:
    beq   x10, x0, DELAY_DONE
    lui   x11, 2                # x11 = 8192
    addi  x11, x11, -1442      # x11 = 6750
IC_LOOP:
    addi  x11, x11, -1
    bne   x11, x0, IC_LOOP
    addi  x10, x10, -1
    jal   x0, DELAY_MS
DELAY_DONE:
    jalr  x0, x1, 0

# ── LED_ON / LED_OFF ──────────────────────────────────────────────
LED_ON:
    lui   x14, 0x2000           # x14 = 0x02000000
    addi  x15, x0, 1
    sw    x15, 0(x14)
    jalr  x0, x1, 0

LED_OFF:
    lui   x14, 0x2000
    sw    x0, 0(x14)
    jalr  x0, x1, 0

# ── SEND_DIT — nokta: 200ms ac, 200ms kapali ──────────────────────
SEND_DIT:
    addi  sp, sp, -4
    sw    x1, 0(sp)

    jal   x1, LED_ON
    addi  x10, x0, 200
    jal   x1, DELAY_MS

    jal   x1, LED_OFF
    addi  x10, x0, 200
    jal   x1, DELAY_MS

    lw    x1, 0(sp)
    addi  sp, sp, 4
    jalr  x0, x1, 0

# ── SEND_DAH — cizgi: 600ms ac, 200ms kapali ──────────────────────
SEND_DAH:
    addi  sp, sp, -4
    sw    x1, 0(sp)

    jal   x1, LED_ON
    addi  x10, x0, 600          # 600 < 2047, gecerli
    jal   x1, DELAY_MS

    jal   x1, LED_OFF
    addi  x10, x0, 200
    jal   x1, DELAY_MS

    lw    x1, 0(sp)
    addi  sp, sp, 4
    jalr  x0, x1, 0

# ── SEND_WORD_SPACE — kelimeler arasi: 1400ms ─────────────────────
# 1400 > 2047 yok, 1400 < 2047 gecerli
SEND_WORD_SPACE:
    addi  sp, sp, -4
    sw    x1, 0(sp)

    addi  x10, x0, 1400
    jal   x1, DELAY_MS

    lw    x1, 0(sp)
    addi  sp, sp, 4
    jalr  x0, x1, 0

# ── SEND_CHAR — tek harf gonder ───────────────────────────────────
# x10 = ASCII karakter (A=0x41 .. Z=0x5A)
SEND_CHAR:
    addi  sp, sp, -20
    sw    x1,  0(sp)
    sw    x12, 4(sp)
    sw    x13, 8(sp)
    sw    x10, 12(sp)
    sw    x14, 16(sp)

    # indeks = karakter - 'A'
    addi  x11, x0, 65
    sub   x11, x10, x11         # x11 = indeks (0..25)

    # MORSE_TABLE[indeks] adresini hesapla
    # MORSE_TABLE = 0x00008000
    lui   x12, 0x8              # x12 = 0x00008000
    slli  x11, x11, 2           # indeks * 4
    add   x12, x12, x11
    lw    x12, 0(x12)           # x12 = morse word

    # sembol sayisi = word[15:8]
    srli  x13, x12, 8
    andi  x13, x13, 0xFF        # x13 = sembol sayisi
    andi  x12, x12, 0xFF        # x12 = pattern (LSB = ilk sembol)

SYMBOL_LOOP:
    beq   x13, x0, CHAR_DONE

    andi  x11, x12, 1           # LSB: 0=dit, 1=dah
    beq   x11, x0, DO_DIT

DO_DAH:
    jal   x1, SEND_DAH
    jal   x0, NEXT_SYM

DO_DIT:
    jal   x1, SEND_DIT

NEXT_SYM:
    srli  x12, x12, 1           # pattern >> 1
    addi  x13, x13, -1
    jal   x0, SYMBOL_LOOP

CHAR_DONE:
    # harf sonu ek bosluk: 600ms toplam olsun, son sembol sonu zaten
    # 200ms bosluk birakti, 400ms daha ekle
    addi  x10, x0, 400
    jal   x1, DELAY_MS

    lw    x1,  0(sp)
    lw    x12, 4(sp)
    lw    x13, 8(sp)
    lw    x10, 12(sp)
    lw    x14, 16(sp)
    addi  sp, sp, 20
    jalr  x0, x1, 0
