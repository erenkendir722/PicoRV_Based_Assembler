# main.asm — Fibonacci ana döngüsü
#
# FIB_STEP fonksiyonunu math.asm'den çağırır.
# Sonuçları .data bölümündeki FIB_ARR dizisine yazar.
#
# Register sözleşmesi:
#   x1  = dönüş adresi (ra)
#   x10 = fonksiyon argümanı / dönüş değeri (a0)
#   x11 = geçici (a1)
#
# Fib dizisi: 0, 1, 1, 2, 3, 5, 8, 13, 21, 34  (ilk 10 eleman)

.global MAIN
.extern FIB_STEP

.text
.org 0x00000000

# ── Başlangıç ──────────────────────────────────────
MAIN:
    addi  x10, x0, 0       # fib(0) = 0  → önceki
    addi  x11, x0, 1       # fib(1) = 1  → şimdiki
    addi  x5,  x0, 10      # sayaç = 10 (üretilecek eleman sayısı)
    lui   x6,  16           # x6 = 0x10000 → FIB_ARR taban adresi
    addi  x7,  x0, 0        # dizi indeks offset (byte)

# İlk iki elemanı elle yaz (fib(0) ve fib(1))
    sw    x10, 0(x6)        # FIB_ARR[0] = 0
    sw    x11, 4(x6)        # FIB_ARR[1] = 1
    addi  x7,  x7, 8        # offset += 2 * 4
    addi  x5,  x5, -2       # kalan eleman = 8

# ── Döngü ──────────────────────────────────────────
LOOP:
    beq   x5,  x0, DONE    # sayaç == 0 → bitti

    # FIB_STEP(önceki=x10, şimdiki=x11) → yeni değer x10'da döner
    # Çağırmadan önce x5/x6/x7/x11'i yığına kaydet
    addi  sp, sp, -20
    sw    x1,  0(sp)
    sw    x5,  4(sp)
    sw    x6,  8(sp)
    sw    x7,  12(sp)
    sw    x11, 16(sp)

    jal   x1, FIB_STEP      # x10 = önceki + şimdiki

    lw    x1,  0(sp)
    lw    x5,  4(sp)
    lw    x6,  8(sp)
    lw    x7,  12(sp)
    lw    x11, 16(sp)
    addi  sp, sp, 20

    # Yeni Fibonacci değerini diziye yaz
    add   x8, x6, x7        # adres = taban + offset
    sw    x10, 0(x8)        # FIB_ARR[i] = yeni_fib

    # Slide: önceki = şimdiki, şimdiki = yeni
    addi  x10, x11, 0       # önceki = eski şimdiki
    # x10 (yeni fib) şimdiki olacak — geçici sakla
    lw    x11, 0(x8)        # şimdiki = yeni_fib

    addi  x7, x7, 4         # offset += 4
    addi  x5, x5, -1        # sayaç--
    jal   x0, LOOP

DONE:
    ebreak                  # program bitti

.data
.org 0x10000
FIB_ARR: .word 0            # [0]  eleman 0
         .word 0            # [1]  eleman 1
         .word 0            # [2]  eleman 2
         .word 0            # [3]  eleman 3
         .word 0            # [4]  eleman 4
         .word 0            # [5]  eleman 5
         .word 0            # [6]  eleman 6
         .word 0            # [7]  eleman 7
         .word 0            # [8]  eleman 8
         .word 0            # [9]  eleman 9
