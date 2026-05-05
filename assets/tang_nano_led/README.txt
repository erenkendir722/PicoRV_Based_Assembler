Tang Nano 9K — LED Binary Sayac Demo
======================================

AMAC
-----
PicoRV32 RV32I islemcisi uzerinde calisan, 6 LED'i binary sayac
olarak surduran cok dosyali assembly demosu.

LED davranisi:
  0b000000 (0)  → tum LEDler sonuk
  0b000001 (1)  → LED0 yanik
  0b000010 (2)  → LED1 yanik
  ...
  0b111111 (63) → tum LEDler yanik
  Sonra tekrar 0'a doner.

Her adim arasi ~200 ms bekleme (27 MHz dahili osilatorde).


DOSYALAR
---------
  main.asm    Ana program: sayac dongusu, GPIO yazma, DELAY_MS cagrisi
  utils.asm   Yardimci: DELAY_MS fonksiyonu (yazilim tabanli bekleme)
  memory.ld   Linker script: text=0x0, data=0x8000


LINKLEME
---------
1. Assembler GUI'yi ac (python RV32I.py)
2. Sol panelden tang_nano_led klasorunu ac
3. main.asm ve utils.asm'yi isaretcikle sec
4. memory.ld'yi linker script olarak yukle
5. "Build" butonuna bas
6. .mem sekmesinden ciktiyi "export" et


FPGA YUKLEME (Gowin IDE)
--------------------------
1. Gowin IDE'de yeni proje ac (GW1NR-9C, Tang Nano 9K)
2. PicoRV32 kaynak kodunu ekle (picorv32.v)
3. BRAM wrapper'a memory.mem dosyasini init olarak ver:
     $readmemh("memory.mem", mem);
4. LED GPIO cikisini sentezle:
     assign LED = gpio_out[5:0];  // aktif-dusuk ise: ~gpio_out[5:0]
5. Tang Nano 9K pin constraint dosyasini (.cst) uygula:
     IO_LOC "LED[0]" 10;
     IO_LOC "LED[1]" 11;
     IO_LOC "LED[2]" 13;
     IO_LOC "LED[3]" 14;
     IO_LOC "LED[4]" 15;
     IO_LOC "LED[5]" 16;
6. Sentez + Yerlesim + Rota calistir
7. Gowin Programmer ile bitstream yukle


TANG NANO 9K GPIO BELLEK ADRESI
---------------------------------
PicoRV32 custom memory map (SoC tasariminiza gore degisebilir):
  0x02000000 = GPIO cikis register
               bit[5:0] → LED5..LED0
               0 = LED yanik (aktif-dusuk), 1 = LED sonuk
