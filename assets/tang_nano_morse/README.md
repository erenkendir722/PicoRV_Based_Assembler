# tang_nano_morse

Tang Nano 9K FPGA üzerinde çalışan, PicoRV32 işlemcisiyle yazılmış RV32I assembly Mors kodu göndericisi. İstediğiniz metni tek bir komutla derleyip FPGA'ya yükleyebilirsiniz.

---

## Nasıl Kullanılır

```bash
# Proje kökünden çalıştırın
python _build_morse.py "MESAJ"

# Örnekler
python _build_morse.py "SOS"
python _build_morse.py "MERHABA DUNYA"
python _build_morse.py "CQ DE TA1ABC"
```

Sadece **A–Z harfleri** ve **boşluk** kabul edilir. Script `gowin_project/program.mem` dosyasını üretir; bunu Gowin Programmer ile FPGA'ya yükleyin.

---

## Dosya Yapısı

```
tang_nano_morse/
├── main.asm              Ana program — mesaj döngüsü
├── morse.asm             Mors fonksiyonları — dit, dah, harf, kelime
├── morse_table.asm       Alfabe tablosu + mesaj (build script tarafından üretilir)
├── memory.ld             Linker script — bellek adresleri
└── gowin_project/
    ├── top.v             SoC — PicoRV32 + BSRAM + GPIO
    ├── bram_mem.v        2 KB BSRAM modülü
    ├── picorv32.v        PicoRV32 işlemci çekirdeği
    ├── tang_nano_9k.cst  FPGA pin kısıtlamaları
    └── program.mem       Derleme çıktısı ($readmemh formatı)
```

---

## Donanım

**Tang Nano 9K** — Gowin GW1NR-9C FPGA
- 27 MHz dahili osilatör
- 6 kullanıcı LED'i (pin 10–16)
- FT2232H USB: Interface 0 = JTAG, Interface 1 = UART

**PicoRV32** — RISC-V RV32I soft-core işlemci
- 2 KB BSRAM: adres `0x000–0x7FF` (512 word)
- Tüm kod, veri ve yığın bu 2 KB içine sığar

### LED Görevleri

| LED | Pin | Ne zaman |
|-----|-----|----------|
| LED0 | 10 | Morse sinyali — nokta/çizgi sırasında yanar |
| LED4 | 15 | Kelime sonu — kelimeler arası 1400 ms beklerken LED4+LED5 birlikte yanar |
| LED5 | 16 | Harf sonu — harfler arası 400 ms beklerken yanar |

---

## Bellek Haritası

```
0x00000000 ┬─ .text başlangıcı
           │  main.asm     (~22 komut, ~88 byte)
0x00000200 ├─ morse.asm    (~60 komut, ~240 byte)
0x00000400 ├─ .data başlangıcı
           │  MORSE_TABLE  26 × 4 byte = 104 byte   (A–Z encoding)
0x00000468 ├─ MSG_TABLE    mesaj + 0xFF sonlandırıcı
           │  (her karakter 1 word = 4 byte)
           ┆
0x000007F0 └─ stack pointer başlangıcı (aşağı büyür)
0x000007FF    BSRAM sonu
```

`0x02000000` — GPIO yazmacı (memory-mapped I/O)
- `bit 0` = LED0
- `bit 4` = LED4
- `bit 5` = LED5

---

## Mors Encoding

`MORSE_TABLE`'da her harf 1 word (32 bit) ile kodlanmıştır:

```
word = (sembol_sayısı << 8) | pattern
```

- `sembol_sayısı` (üst byte): kaç dit/dah var (1–4)
- `pattern` (alt byte): her bit bir sembolü temsil eder, `0` = nokta, `1` = çizgi, **LSB ilk sembol**

**Örnek — R harfi ( . - . ):**
```
sembol_sayısı = 3
pattern       = 0b010  →  bit0=0(dit), bit1=1(dah), bit2=0(dit)
word          = 0x0302
```

`SEND_CHAR` fonksiyonu bu word'ü okur, `pattern`'ı LSB'den başlayarak bit bit işler.

---

## Zamanlama

27 MHz saat, `DELAY_MS` fonksiyonu her milisaniye için 6750 iç döngü iterasyonu çalıştırır.

```
6750 iter × (4 komut / iter) = 27000 komut = 27 MHz × 1 ms  ✓
```

| Olay | Süre |
|------|------|
| DIT (nokta) açık | 200 ms |
| DIT sonrası sessizlik | 200 ms |
| DAH (çizgi) açık | 600 ms |
| DAH sonrası sessizlik | 200 ms |
| Harf sonu ek bekleme | 400 ms (toplamda 600 ms sessizlik) |
| Kelime sonu bekleme | 1400 ms |
| Mesaj sonu bekleme | ~3000 ms |

---

## Assembler & Linker Pipeline

Proje kendi Python assembler/linker'ını kullanır (`core/` dizini).

### Adım 1 — Assembly (3 dosya ayrı derlenir)

Her `.asm` dosyası `Assembler` sınıfıyla iki geçişte derlenir:

- **Pass 1:** Label adreslerini toplar, location counter hesaplar
- **Pass 2:** Her komutu 32-bit makine koduna çevirir; `extern` referanslar için relocation kaydı oluşturur

Her dosya bir `ObjectFile` üretir:
```
ObjectFile {
  text: [(adres, word, boyut), ...]   ← .text section
  data: [(adres, word, boyut), ...]   ← .data section
  globals: {"SEND_CHAR": 0x...}       ← dışa açık semboller
  externs: ["MORSE_TABLE", ...]       ← dışarıdan beklenen semboller
  relocations: [(adres, "LABEL", tip)]← çözülmemiş referanslar
}
```

### Adım 2 — Linking

`Linker`, üç `ObjectFile`'ı birleştirir:

1. **Section yerleştirme:** `.text` section'ları `0x00000000`'dan, `.data` section'ları `0x00000400`'dan sırayla yerleştirilir
2. **Global sembol tablosu:** Her dosyanın dışa açık sembolleri tek tabloda birleştirilir
3. **Relocation:** `extern` referanslar gerçek adresleriyle yamanır

Yamama tipleri:
- `J` — JAL komutu (20-bit PC-relative)
- `B` — Branch komutu (12-bit PC-relative)
- `I` — I-type immediate (12-bit mutlak)
- `ABS` — mutlak adres

### Adım 3 — program.mem üretimi

Bağlanan binary, Gowin'in `$readmemh` okuyabileceği formata dönüştürülür:

```
@00000000      ← word adresi (byte adres / 4)
00000413       ← 32-bit hex word
00007F13
...
@00000100      ← boşluk varsa yeni segment başlığı
...
```

`bram_mem.v` içindeki `initial $readmemh("program.mem", mem, 0, 511);` satırı bu dosyayı okuyarak BSRAM'i başlatır.

---

## Çalışma Akışı (Assembly'den LED'e)

```
_build_morse.py "SOS"
        │
        ├─ main.asm    ──┐
        ├─ morse.asm   ──┼──► Assembler ──► ObjectFile × 3
        └─ (üretilen)  ──┘
           morse_table.asm
                │
                ▼
             Linker
                │
                ├─► program.mem  ──► Gowin Programmer ──► FPGA BSRAM
                └─► output.hex   (debug için)
                        │
                        ▼
              FPGA açılır, PicoRV32 0x000'dan başlar
                        │
                        ▼
              MAIN: sp = 0x7F0
              MSG_LOOP: MSG_TABLE[0x468] oku
                        │
                  ┌─────┴──────┐
                  │            │
               harf          boşluk
                  │            │
             SEND_CHAR    SEND_WORD_SPACE
                  │            │
           SYMBOL_LOOP   LED4+LED5 yak
           bit bit oku    1400ms bekle
                  │       LED söndür
            0→SEND_DIT
            1→SEND_DAH
                  │
            CHAR_DONE
            LED5 yak
            400ms bekle
            LED söndür
```

---

## FPGA'ya Yükleme

### Gowin Programmer ile

1. Gowin IDE açın → **Programmer** sekmesi
2. **Add Device** → Tang Nano 9K seçin
3. **Operation** → `embFlash` → `Program`
4. **File** olarak `gowin_project/program.mem` **değil**, sentez çıktısı `.fs` dosyasını seçin

> **Not:** `program.mem` doğrudan yüklenmez. Gowin sentezi sırasında Verilog'daki `$readmemh` direktifi bu dosyayı okuyarak BSRAM içeriğini `.fs` bitstream'ine gömer. Bu yüzden **mesaj değiştirince Gowin'de yeniden sentez yapmanız gerekir**.

### Sentez Adımları

1. `_build_morse.py` ile `program.mem` üretin
2. Gowin IDE'de projeyi açın (veya `top.v`, `bram_mem.v`, `picorv32.v` dosyalarını ekleyin)
3. **Run All** (Synthesize → Place & Route → Bitstream)
4. Üretilen `.fs` dosyasını Programmer ile FPGA'ya yükleyin

### openFPGALoader ile (Mac/Linux)

```bash
openFPGALoader -b tangnano9k impl/pnr/fpga_project.fs
```

Windows'ta libusbK sürücüsü gerekir (Zadig ile Interface 0'a yükleyin).

---

## Mesajı Değiştirmek

```bash
# Sadece bu kadar yeterli:
python _build_morse.py "YENI MESAJ"
# → morse_table.asm güncellenir
# → gowin_project/program.mem üretilir
# Ardından Gowin'de yeniden sentez yapın
```

Geçerli karakterler: `A–Z` ve boşluk. Küçük harf otomatik büyütülür.
