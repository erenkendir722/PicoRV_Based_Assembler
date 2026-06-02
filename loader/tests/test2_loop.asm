# ════════════════════════════════════════════════════════════════════
# TEST 2 — DONGU  (sartli dallanma ile iteratif toplama)
# ════════════════════════════════════════════════════════════════════
# Amac: Loader'in dallanma (branch) komutlari iceren, bellek siniri
#       boyunca dogru adreslenmis bir programi calistirdigini gostermek.
#
# Hesap: sonuc = 1 + 2 + 3 + ... + 8 = 36
#        36 = 0b100100
#
# Cikis:
#   * LED register (0x02000000) <- 36
#   * UART (0x03000000) <- 36
# ════════════════════════════════════════════════════════════════════

.global MAIN
.text
.org 0x00000000

MAIN:
    lui   x6, 0x2000           # x6 = LED tabani
    lui   x7, 0x3000           # x7 = UART tabani

    # ── Toplam dongusu: sum = 0 ; i = 1..8 ──────────────────────
    addi  x5,  x0, 0           # x5 = sum = 0
    addi  x10, x0, 1           # x10 = i = 1
    addi  x11, x0, 9           # x11 = sinir (i < 9)

LOOP:
    add   x5,  x5, x10         # sum += i
    addi  x10, x10, 1          # i++
    bne   x10, x11, LOOP       # i != 9 ise devam   (sum = 36)

    # ── LED'e yaz ────────────────────────────────────────────────
    sw    x5, 0(x6)

    # ── UART ile gonder ──────────────────────────────────────────
UWAIT:
    lw    x12, 0(x7)
    andi  x12, x12, 1
    bne   x12, x0, UWAIT
    sw    x5, 0(x7)            # sonuc baytini (36) gonder

HALT:
    jal   x0, HALT
