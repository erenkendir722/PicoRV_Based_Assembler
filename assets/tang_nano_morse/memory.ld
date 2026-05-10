/* RV32I Linker Script — Tang Nano 9K / PicoRV32 Mors Kodu Demo
 *
 * Bellek Haritasi:
 *   0x00000000 — .text : makine kodu (BSRAM)
 *   0x00000400 — .data : mors tablosu + mesaj (BSRAM)
 */

MEMORY {
    text_base = 0x00000000;
    data_base = 0x00000400;
}
