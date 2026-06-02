# ════════════════════════════════════════════════════════════════════
# TEST 3 — FONKSIYON CAGRISI + YIGIN (stack) + IC ICE CAGRI
# ════════════════════════════════════════════════════════════════════
# Amac: Loader'in en karmasik senaryoyu — jal/jalr ile fonksiyon cagrisi,
#       yigin uzerinde register saklama/geri yukleme ve ic ice (nested)
#       cagri iceren bir programi — dogru calistirdigini gostermek.
#
# Hesap: Fibonacci(10) = 55       (0b110111)
#        MAIN -> FIB(10) -> her adimda STEP(prev,cur) leaf fonksiyonu
#
# Cikis:
#   * LED register (0x02000000) <- 55
#   * UART (0x03000000) <- 55
#
# Calisma sartlari:
#   * sp (x2) reset'te STACKADDR = 0x00000FF0 olarak ayarlanir (picorv32).
#   * Cagri sozlesmesi: a0=arg/donus, ra=donus adresi, s1..s4 callee-saved.
# ════════════════════════════════════════════════════════════════════

.global MAIN
.text
.org 0x00000000

MAIN:
    lui   x6, 0x2000           # LED tabani
    lui   x7, 0x3000           # UART tabani

    addi  a0, x0, 10           # a0 = n = 10
    jal   ra, FIB              # a0 = fib(10) = 55

    # ── Sonucu LED + UART'a yaz ──────────────────────────────────
    sw    a0, 0(x6)            # LED <- 55
UWAIT:
    lw    t0, 0(x7)
    andi  t0, t0, 1
    bne   t0, x0, UWAIT
    sw    a0, 0(x7)            # UART <- 55

HALT:
    jal   x0, HALT


# ─────────────────────────────────────────────────────────────────
# FIB(n)  :  a0 = n  ->  donus a0 = fib(n)
#   Iteratif; her adimda STEP leaf fonksiyonunu cagirir (ic ice cagri).
#   Yiginda ra, s1..s4 saklanir/geri yuklenir.
#   Degiskenler: s1=i, s2=prev, s3=cur, s4=n
# ─────────────────────────────────────────────────────────────────
FIB:
    addi  sp, sp, -20          # yigin cercevesi ac (5 word)
    sw    ra, 16(sp)
    sw    s1, 12(sp)
    sw    s2, 8(sp)
    sw    s3, 4(sp)
    sw    s4, 0(sp)

    add   s4, x0, a0           # s4 = n
    addi  s2, x0, 0            # s2 = prev = fib(0) = 0
    addi  s3, x0, 1            # s3 = cur  = fib(1) = 1
    addi  s1, x0, 1            # s1 = i = 1

FIBLOOP:
    beq   s1, s4, FIBDONE      # i == n -> bitti
    add   a0, x0, s2           # arg0 = prev
    add   a1, x0, s3           # arg1 = cur
    jal   ra, STEP             # a0 = prev + cur   (IC ICE CAGRI)
    add   s2, x0, s3           # prev = cur
    add   s3, x0, a0           # cur  = next
    addi  s1, s1, 1            # i++
    jal   x0, FIBLOOP

FIBDONE:
    add   a0, x0, s3           # donus = cur = fib(n)
    lw    ra, 16(sp)
    lw    s1, 12(sp)
    lw    s2, 8(sp)
    lw    s3, 4(sp)
    lw    s4, 0(sp)
    addi  sp, sp, 20           # yigin cercevesini kapat
    jalr  x0, ra, 0            # return


# ─────────────────────────────────────────────────────────────────
# STEP(a, b)  :  a0 = a, a1 = b  ->  donus a0 = a + b   (leaf)
# ─────────────────────────────────────────────────────────────────
STEP:
    add   a0, a0, a1
    jalr  x0, ra, 0            # return
