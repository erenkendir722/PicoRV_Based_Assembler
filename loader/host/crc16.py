"""
crc16.py — CRC-16/CCITT-FALSE

Host (Python) ve FPGA (Verilog loader.v) taraflarinda BIREBIR ayni hesap
kullanilir. Bu sayede seri port uzerinden gonderilen her paketin butunlugu
dogrulanabilir (Proje 3: "veri kaybini onlemek icin Checksum/CRC").

Parametreler (CRC-16/CCITT-FALSE):
    polinom  = 0x1021
    baslangic = 0xFFFF
    yansima  = yok (no reflection)
    son XOR  = yok
"""

POLY = 0x1021
INIT = 0xFFFF


def crc16_update(crc: int, byte: int) -> int:
    """Tek bir bayt isleyip yeni CRC degerini dondurur (Verilog ile ayni)."""
    crc ^= (byte & 0xFF) << 8
    for _ in range(8):
        if crc & 0x8000:
            crc = ((crc << 1) ^ POLY) & 0xFFFF
        else:
            crc = (crc << 1) & 0xFFFF
    return crc


def crc16(data: bytes, crc: int = INIT) -> int:
    """Bir bayt dizisinin CRC-16/CCITT-FALSE degerini hesaplar."""
    for b in data:
        crc = crc16_update(crc, b)
    return crc & 0xFFFF


if __name__ == "__main__":
    # Standart dogrulama vektoru: "123456789" -> 0x29B1
    test = b"123456789"
    val = crc16(test)
    print(f'CRC16("123456789") = 0x{val:04X}  (beklenen 0x29B1)')
    assert val == 0x29B1, "CRC-16/CCITT-FALSE dogrulamasi BASARISIZ!"
    print("CRC-16/CCITT-FALSE dogrulamasi GECTI.")
