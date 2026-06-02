# ════════════════════════════════════════════════════════════════════
# TEST 1 — BASIT MATEMATIK  (duz akis, dallanma/fonksiyon yok)
# ════════════════════════════════════════════════════════════════════
# Amac: Loader'in en temel programi (lineer aritmetik) dogru yukleyip
#       calistirdigini gostermek.
#
# Hesap: sonuc = (6 + 7) = 13
#        13 = 0b001101
#
# Cikis:
#   * LED register (0x02000000) <- sonuc  (yanan LED = ikilik 1)
#   * UART veri portu (0x03000000) <- sonuc baytini host'a gonder
#
# Bellek haritasi (top_loader.v):
#   0x02000000 : GPIO LED  (write: bit[5:0] = LED5..LED0, donanim aktif-dusuk)
#   0x03000000 : UART veri (write: bit[7:0] gonderilir; read: bit0 = tx_busy)
# ════════════════════════════════════════════════════════════════════

.global MAIN
.text
.org 0x00000000

MAIN:
    lui   x6, 0x2000           # x6 = 0x02000000  (LED tabani)
    lui   x7, 0x3000           # x7 = 0x03000000  (UART tabani)

    # ── Aritmetik ────────────────────────────────────────────────
    addi  x5,  x0, 6           # x5 = 6
    addi  x8,  x0, 7           # x8 = 7
    add   x5,  x5, x8          # x5 = 13   (SONUC)

    # ── LED'e yaz (gercek deger; donanim aktif-dusuk cevirir) ─────
    sw    x5, 0(x6)

    # ── UART ile sonucu host'a gonder ────────────────────────────
UWAIT:
    lw    x11, 0(x7)           # tx durumunu oku
    andi  x11, x11, 1          # bit0 = busy
    bne   x11, x0, UWAIT       # busy ise bekle
    sw    x5, 0(x7)            # sonuc baytini (13) gonder

HALT:
    jal   x0, HALT             # sonsuz dongu (program bitti)
