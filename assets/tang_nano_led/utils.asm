# utils.asm — Tang Nano 9K Yardimci Fonksiyonlar
#
# DELAY_MS: Milisaniye cinsinden yazilim tabanli bekleme fonksiyonu.
#
# PicoRV32 @ 27 MHz (Tang Nano 9K dahili osilatoru)
#   1 ms = 27.000 cevrim
#   Dongu govdesi: ~4 komut = 4 cevrim
#   Ic dongu tekrar sayisi = 27000 / 4 = 6750
#
# Giris:
#   x10 (a0) = bekleme suresi (milisaniye)
# Cikis: yok
# Degistirilen registerlar: x10, x11, x12 (caller-saved)
# ─────────────────────────────────────────────────────────────────

.global DELAY_MS

.text
.org 0x00000200             # main'den sonra yerlesir

DELAY_MS:
    # x10 = ms sayaci (kalan ms)
    # ic dongu: 1 ms = IC_COUNT cevrim
    # IC_COUNT = 27000 / 4 komut ~= 6750

MS_LOOP:
    beq   x10, x0, DELAY_DONE  # ms == 0 ise bitti

    # Ic dongu: 1 ms bekleme
    addi  x11, x0, 0x1A5E      # x11 = 6750 (ic sayac)
                                # 0x1A5E = 6750
IC_LOOP:
    addi  x11, x11, -1         # sayac--
    bne   x11, x0, IC_LOOP     # != 0 ise ic dongude kal

    addi  x10, x10, -1         # ms sayaci--
    jal   x0, MS_LOOP          # bir sonraki ms'e gec

DELAY_DONE:
    jalr  x0, x1, 0            # return
