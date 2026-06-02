#!/usr/bin/env python3
"""
loader_host.py — Bilgisayar Tarafi (Host Application)  [Proje 3]
════════════════════════════════════════════════════════════════════════
Linker'dan cikan .bin program imajini okur, CRC-16'li paketler halinde seri
port uzerinden Tang Nano 9K'daki Loader FSM'e gonderir; her paket icin ACK
bekler, NACK/zaman asiminda paketi yeniden gonderir. Tum paketler yuklenince
RUN komutu gondererek CPU'yu calistirir ve programin UART'tan dondurdugu
sonucu ekrana basar.

── Paket protokolu (loader.v ile birebir) ──────────────────────────────
  WRITE: AA 55 01 ADDR[31:0](BE) NWORDS DATA(4*N, BE word) CRC16_HI CRC16_LO
  RUN  : AA 55 02 CRC16_HI CRC16_LO
  Cevap: ACK=0x06  NACK=0x15
  CRC  : CRC-16/CCITT-FALSE, [CMD .. son veri bayti] uzerinden.

── Kullanim ────────────────────────────────────────────────────────────
  python loader_host.py --port /dev/tty.usbserial-XXXX --file ../build/test3_func.bin
  python loader_host.py --port COM5 --file ../build/test1_math.bin --baud 115200 --listen
"""
import argparse
import sys
import time

try:
    import serial   # pyserial
except ImportError:
    print("HATA: pyserial gerekli ->  pip install pyserial")
    sys.exit(1)

from crc16 import crc16, INIT, crc16_update

# ── Protokol sabitleri ──────────────────────────────────────────────────
SYNC0, SYNC1 = 0xAA, 0x55
CMD_WRITE, CMD_RUN = 0x01, 0x02
ACK, NACK = 0x06, 0x15


def build_write_packet(base_addr: int, words: list[int]) -> bytes:
    """Bir WRITE paketi olusturur (CRC dahil)."""
    n = len(words)
    assert 1 <= n <= 255, "paket basina 1..255 word"
    body = bytearray()
    body.append(CMD_WRITE)
    body += base_addr.to_bytes(4, "big")
    body.append(n)
    for w in words:
        body += (w & 0xFFFFFFFF).to_bytes(4, "big")   # big-endian word
    crc = crc16(bytes(body))                           # CMD..DATA uzerinden
    return bytes([SYNC0, SYNC1]) + bytes(body) + crc.to_bytes(2, "big")


def build_run_packet() -> bytes:
    """RUN paketi (CPU reset'i serbest birakir)."""
    crc = crc16_update(INIT, CMD_RUN)
    return bytes([SYNC0, SYNC1, CMD_RUN]) + crc.to_bytes(2, "big")


def read_words_from_bin(path: str) -> list[int]:
    """Duz little-endian .bin dosyasini 32-bit word listesine cevirir."""
    with open(path, "rb") as f:
        data = f.read()
    if len(data) % 4 != 0:
        data += b"\x00" * (4 - len(data) % 4)   # 4'e tamamla
    return [int.from_bytes(data[i:i+4], "little") for i in range(0, len(data), 4)]


def send_packet(ser, packet: bytes, retries: int, timeout: float) -> bool:
    """Paketi gonderir, ACK bekler; NACK/zaman asiminda yeniden dener."""
    for attempt in range(1, retries + 1):
        ser.reset_input_buffer()
        ser.write(packet)
        ser.flush()
        deadline = time.time() + timeout
        while time.time() < deadline:
            resp = ser.read(1)
            if not resp:
                continue
            if resp[0] == ACK:
                return True
            if resp[0] == NACK:
                print(f"    NACK alindi, yeniden gonderiliyor (deneme {attempt}/{retries})")
                break
        else:
            print(f"    zaman asimi, yeniden gonderiliyor (deneme {attempt}/{retries})")
    return False


def main():
    ap = argparse.ArgumentParser(description="PicoRV32 UART Loader — Host gonderici")
    ap.add_argument("--port", required=True, help="seri port (orn. /dev/tty.usbserial-XXXX, COM5)")
    ap.add_argument("--file", required=True, help="yuklenecek .bin program imaji")
    ap.add_argument("--baud", type=int, default=115200, help="baud hizi (varsayilan 115200)")
    ap.add_argument("--addr", type=lambda x: int(x, 0), default=0x00000000,
                    help="yukleme baz adresi (varsayilan 0x0)")
    ap.add_argument("--chunk", type=int, default=64, help="paket basina word (varsayilan 64)")
    ap.add_argument("--retries", type=int, default=5, help="paket basina deneme (varsayilan 5)")
    ap.add_argument("--timeout", type=float, default=2.0, help="ACK zaman asimi sn (varsayilan 2.0)")
    ap.add_argument("--no-run", action="store_true", help="RUN gonderme (sadece yukle)")
    ap.add_argument("--listen", action="store_true", help="RUN sonrasi UART ciktisini dinle")
    args = ap.parse_args()

    words = read_words_from_bin(args.file)
    if not words:
        print("HATA: program bos")
        sys.exit(1)

    print(f"Program : {args.file}  ({len(words)} word / {len(words)*4} byte)")
    print(f"Port    : {args.port} @ {args.baud} baud")
    print(f"Baz adr : 0x{args.addr:08X}   paket boyu: {args.chunk} word\n")

    try:
        ser = serial.Serial(args.port, args.baud, timeout=0.1)
    except serial.SerialException as e:
        print(f"HATA: seri port acilamadi: {e}")
        sys.exit(1)

    time.sleep(0.2)  # port stabilize

    t0 = time.time()
    sent = 0
    for i in range(0, len(words), args.chunk):
        chunk = words[i:i + args.chunk]
        addr = args.addr + i * 4
        pkt = build_write_packet(addr, chunk)
        if not send_packet(ser, pkt, args.retries, args.timeout):
            print(f"HATA: paket @0x{addr:08X} gonderilemedi (ACK yok). Iptal.")
            ser.close()
            sys.exit(1)
        sent += len(chunk)
        print(f"  WRITE @0x{addr:08X}  {len(chunk):>3} word  -> ACK   ({sent}/{len(words)})")

    elapsed = time.time() - t0
    print(f"\nYukleme tamam: {sent} word, {sent*4} byte, {elapsed*1000:.1f} ms "
          f"(~{sent*4/elapsed/1024:.1f} KB/s)")

    if not args.no_run:
        if send_packet(ser, build_run_packet(), args.retries, args.timeout):
            print("RUN -> ACK  (CPU calismaya basladi, PC=0x0)")
        else:
            print("HATA: RUN onaylanmadi")
            ser.close()
            sys.exit(1)

    if args.listen:
        print("\nProgram UART ciktisi (Ctrl-C ile cik):")
        try:
            ser.timeout = 1.0
            while True:
                b = ser.read(1)
                if b:
                    print(f"  <- {b[0]:>3} (0x{b[0]:02X})")
        except KeyboardInterrupt:
            print("\nDinleme sonlandirildi.")

    ser.close()


if __name__ == "__main__":
    main()
