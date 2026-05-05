# main.asm — Tang Nano 9K LED Binary Sayac
#
# PicoRV32 uzerinde 6 LED'i binary sayac olarak surmek icin
# tasarlanmis cok dosyali demo program.
#
# Tang Nano 9K GPIO Bellek Haritasi (PicoRV32 custom memory map):
#   0x02000000 — GPIO cikis register (bit[5:0] = LED5..LED0)
#                LED aktif-dusuk: 0 = yaniyor, 1 = sonuk
#
# Bagimliliklari:
#   delay_ms   : utils.asm'de tanimlı, x10 = ms cinsinden bekleme suresi
#
# Register sozlesmesi:
#   x1  (ra) = donus adresi
#   x5  (t0) = sayac (0..63)
#   x6  (t1) = GPIO taban adresi
#   x10 (a0) = fonksiyon argumani
# ─────────────────────────────────────────────────────────────────

.global MAIN
.extern DELAY_MS

.text
.org 0x00000000

MAIN:
    # GPIO taban adresini yukle: 0x02000000
    lui   x6,  0x2000           # x6 = 0x02000000

    # Sayaci sifirla
    addi  x5, x0, 0             # x5 = 0 (LED pattern)

LOOP:
    # LED degerini GPIO'ya yaz (aktif-dusuk: degeri terse cevir)
    addi  x7, x0, 63            # x7 = 0b111111 (6-bit maske)
    xor   x8, x5, x7            # x8 = ~x5 (aktif-dusuk icin)
    sw    x8, 0(x6)             # GPIO yazma: LED'leri guncelle

    # DELAY_MS(300) — 300 ms bekle
    addi  sp, sp, -4
    sw    x1, 0(sp)             # ra'yi yigina kaydet
    addi  x10, x0, 0xC8        # x10 = 200 ms (delay argumani)
    jal   x1, DELAY_MS

    lw    x1, 0(sp)             # ra'yi geri yukle
    addi  sp, sp, 4

    # Sayaci artir, 63'u gecerse sifirla (6-bit dongusu)
    addi  x5, x5, 1
    addi  x9, x0, 64            # x9 = 64
    bne   x5, x9, LOOP          # x5 != 64 ise donguye devam
    addi  x5, x0, 0             # x5 = 0 (sifirla)
    jal   x0, LOOP              # donguden cikma

.data
.org 0x00008000

# Veri bolumu (ileride kullanim icin rezerve)
DUMMY: .word 0
