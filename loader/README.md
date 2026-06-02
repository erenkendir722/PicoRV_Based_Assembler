# PicoRV32 UART Loader — Proje 3

**PicoRV İşlemci Alt Kümesi (RV32I) için FPGA Tabanlı Loader Tasarımı**

Bilgisayardaki Python betiği, linker'dan çıkan makine kodunu **seri port (UART)** üzerinden
**paketler halinde** Tang Nano 9K FPGA'ine gönderir. FPGA üzerindeki **Loader FSM** paketleri
**CRC-16** ile doğrular, programı **BRAM**'e yazar ve yükleme bitince **PicoRV32 işlemcisini
reset'ten bırakarak** programı fiziksel olarak çalıştırır.

> Proje 2'de program **sentez zamanında** (`$readmemh` ile bitstream'e gömülü) yükleniyordu.
> Proje 3'te program **çalışma zamanında** UART üzerinden canlı yüklenir — yeniden sentez yok.

---

## Mimari

```
  ┌─────────────────────┐         UART (115200 8N1)        ┌──────────────────────────────┐
  │   BİLGİSAYAR (HOST)  │  ── AA 55 01 ADDR N DATA CRC ──▶ │           TANG NANO 9K        │
  │                      │  ◀────────── ACK / NACK ──────── │                              │
  │  loader_host.py      │                                  │  uart_rx ─▶ loader FSM       │
  │   • .bin oku         │                                  │              │  (CRC-16)     │
  │   • paketle + CRC    │                                  │              ▼               │
  │   • ACK bekle/yeniden│                                  │            BRAM (8KB)        │
  │     gönder           │                                  │              │               │
  │   • RUN gönder       │                                  │   cpu_run ──▶ PicoRV32 ─▶ LED│
  │   • sonucu dinle     │  ◀──────── sonuç baytı ───────── │            └──▶ uart_tx       │
  └─────────────────────┘                                  └──────────────────────────────┘
```

Toolchain (Proje 1 + Proje 2 altyapısı):

```
 test*.asm  ──Assembler──▶  ObjectFile  ──Linker──▶  .bin / .words.hex  ──host──▶ FPGA
```

---

## Dosya Yapısı

| Yol | Açıklama |
|---|---|
| `tests/test1_math.asm` | Basit matematik (6+7=13) — düz akış |
| `tests/test2_loop.asm` | Döngü (Σ1..8 = 36) — şartlı dallanma |
| `tests/test3_func.asm` | Fonksiyon çağrısı + yığın (fib(10)=55) — jal/jalr, iç içe çağrı |
| `host/crc16.py` | CRC-16/CCITT-FALSE (host ve FPGA birebir) |
| `host/build_tests.py` | Test programlarını derle+link → `.bin/.words.hex/.lst` |
| `host/loader_host.py` | **Host gönderici** (pyserial + CRC + ACK/retransmit) |
| `rtl/uart_rx.v` | UART alıcı (8N1) |
| `rtl/uart_tx.v` | UART gönderici (8N1) |
| `rtl/loader.v` | **Loader FSM** (paket al, CRC doğrula, BRAM yaz, CPU reset) |
| `rtl/bram_mem.v` | Blok RAM (loader doldurur, `$readmemh` yok) |
| `rtl/top_loader.v` | Üst modül (loader + CPU + BRAM mux + GPIO + UART) |
| `rtl/picorv32.v` | PicoRV32 çekirdeği |
| `rtl/tang_nano_9k.cst` | Fiziksel kısıtlar (clk, UART, LED pinleri) |
| `sim/tb_loader.v` | Uçtan uca self-checking testbench (3 test) |
| `sim/tb_nack.v` | CRC hata kontrolü / NACK + yeniden gönderim testi |
| `sim/run.sh` | Tüm simülasyonları derle + çalıştır |
| `build/` | Üretilen `.bin/.words.hex/.lst` çıktıları |

---

## Paket Protokolü

```
WRITE:  AA 55 01  ADDR[31:0](BE,4B)  NWORDS(1B)  DATA(4*N, BE word)  CRC16_HI CRC16_LO
RUN  :  AA 55 02  CRC16_HI CRC16_LO
Cevap:  ACK = 0x06   |   NACK = 0x15
CRC  :  CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF), [CMD .. son veri baytı] üzerinden
```

- Her WRITE paketi başında 2 senkron baytı (`AA 55`) ile çerçevelenir.
- CRC tutmazsa loader **NACK** döner; host paketi **yeniden gönderir** (veri kaybı önleme).
- RUN doğrulanınca loader CPU reset hattını serbest bırakır; CPU `PC=0x0`'dan başlar.

---

## Kullanım

### 1) Test programlarını derle + linkle
```bash
cd PicoRV_Based_Assembler
python3 loader/host/build_tests.py
# -> loader/build/test{1,2,3}_*.bin / .words.hex / .lst
```

### 2) Simülasyonla doğrula (donanım gerekmez)
```bash
cd loader/sim
./run.sh        # iverilog gerekli: brew install icarus-verilog
```
Beklenen: 3 testte de `SONUC: GECTI` ve NACK testinde CRC reddi + yeniden gönderim.

### 3) FPGA'e sentezle (Gowin EDA)
- Yeni proje: cihaz `GW1NR-LV9QN88PC6/I5`.
- Kaynaklar: `rtl/*.v` (top = `top_loader`), kısıt: `rtl/tang_nano_9k.cst`.
- Sentez → Place&Route → bitstream → Tang Nano 9K'ye programla.
- **UART pinlerini** kartınıza göre `tang_nano_9k.cst` içinde doğrulayın.

### 4) Programı canlı yükle ve çalıştır
```bash
cd loader/host
python3 loader_host.py --port /dev/tty.usbserial-XXXX --file ../build/test3_func.bin --listen
```
- Her paket için `-> ACK`, sonra `RUN -> ACK`, ardından `<- 55 (0x37)` sonucu görünür.
- Tang Nano 9K LED'leri sonucu **ikilik** gösterir (yanan LED = 1). `fib(10)=55 = 0b110111`.

---

## Bellek Haritası (CPU)

| Adres | Bölge | Açıklama |
|---|---|---|
| `0x00000000–0x00001FFF` | BRAM (8 KB) | text + data + stack (sp = `0x00001FF0`) |
| `0x02000000` | GPIO LED | yazma: bit[5:0]=LED5..LED0 (donanım aktif-düşük) |
| `0x03000000` | UART veri | yazma: bit[7:0] gönder; okuma: bit0 = tx_busy |

---

## Doğrulanan Sonuçlar (simülasyon)

| Test | Hesap | Beklenen | UART sonucu | LED | Durum |
|---|---|---|---|---|---|
| test1_math | 6 + 7 | 13 | 13 | `001101` | GEÇTİ |
| test2_loop | Σ(1..8) | 36 | 36 | `100100` | GEÇTİ |
| test3_func | fib(10) | 55 | 55 | `110111` | GEÇTİ |
| tb_nack | bozuk CRC | NACK→ACK | 13 | — | GEÇTİ |

Tüm zincir (host → UART → loader → BRAM → CPU → UART) Icarus Verilog ile uçtan uca doğrulandı.
