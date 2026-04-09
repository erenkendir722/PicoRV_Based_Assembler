# math.asm — Fibonacci yardımcı fonksiyonu
#
# FIB_STEP: Ardışık iki Fibonacci sayısından bir sonrakini hesaplar.
#
# Giriş:
#   x10 (a0) = önceki Fibonacci sayısı  (fib[n-2])
#   x11 (a1) = şimdiki Fibonacci sayısı (fib[n-1])
# Çıkış:
#   x10 (a0) = yeni Fibonacci sayısı    (fib[n] = fib[n-1] + fib[n-2])
#
# Kaydedilen register yok — sadece x10 değişir.

.global FIB_STEP

.text
.org 0x00000200             # main'in text bloğundan sonra yerleşir

FIB_STEP:
    add   x10, x10, x11     # a0 = önceki + şimdiki  (= fib[n])
    jalr  x0,  x1, 0        # return (ra = x1)
