Tang Nano 9K — Mors Kodu LED Demo
====================================

AMAC
-----
Kodlanmis bir metni Mors alfabesiyle LED uzerinden yayinlar.
Su an "SOS" mesajini surekli tekrarlar. Mesaj degistirilebilir.

Mors timing (27 MHz dahili osilatorde):
  DIT (nokta)  = 200 ms LED acik + 200 ms bosluk
  DAH (cizgi)  = 600 ms LED acik + 200 ms bosluk
  Harf sonu    = +400 ms ek bosluk (toplam 600 ms)
  Kelime sonu  = 1400 ms bosluk
  Mesaj sonu   = ~3000 ms bekleme, sonra tekrar

Ornek "SOS":
  S = ...   (dit dit dit)
  O = ---   (dah dah dah)
  S = ...   (dit dit dit)


DOSYALAR
---------
  main.asm        Ana dongü: mesaji okur, SEND_CHAR cagirir
  morse.asm       SEND_CHAR, SEND_DAH, SEND_DIT, DELAY_MS
  morse_table.asm MORSE_TABLE (A-Z encoding) + MSG_TABLE (mesaj)
  memory.ld       Linker script


MESAJI DEGISTIRME
------------------
morse_table.asm dosyasinin sonundaki MSG_TABLE bolumunu duzenle:

  MSG_TABLE:
      .word 0x48   # 'H'
      .word 0x45   # 'E'
      .word 0x4C   # 'L'
      .word 0x4C   # 'L'
      .word 0x4F   # 'O'
      .word 0x20   # ' ' (kelime boslugu)
      .word 0x57   # 'W'
      .word 0x4F   # 'O'
      .word 0x52   # 'R'
      .word 0x4C   # 'L'
      .word 0x44   # 'D'
      .word 0xFF   # bitis

Desteklenen karakterler: A-Z (buyuk), bosluk (0x20)


LINKLEME SIRASI
----------------
GUI'de asagidaki sirayla dosyalari sec (sira onemli):
  1. main.asm
  2. morse.asm
  3. morse_table.asm

memory.ld linker script olarak yukle, Build'e bas.


MODUL BAGIMLILIKLARI
---------------------
  main.asm
    .extern SEND_CHAR       <- morse.asm
    .extern SEND_WORD_SPACE <- morse.asm
    .extern MSG_TABLE       <- morse_table.asm

  morse.asm
    .extern MORSE_TABLE     <- morse_table.asm

  morse_table.asm
    .global MORSE_TABLE
    .global MSG_TABLE


GPIO BELLEK ADRESI
-------------------
  0x02000000 = GPIO register
  bit0 = LED0 (1=yanik, 0=sonuk, aktif-yuksek varsayim)
  PicoRV32 SoC tasariminiza gore bu adres degisebilir.


GELECEK ADIMLAR (v2)
---------------------
  [ ] Buzzer: GPIO bit1 ile ses cikisi ekle (DAH/DIT ayni zamanda)
  [ ] UART RX: Disaridan metin al, gercek zamanli gonder
  [ ] Hiz ayari: DIT_MS degerini bir register'dan oku (potansiyometre)
  [ ] Hem LED hem buzzer cikisi (cift GPIO bit)
