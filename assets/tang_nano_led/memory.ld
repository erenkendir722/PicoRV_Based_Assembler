/* RV32I Linker Script — Tang Nano 9K / PicoRV32
 *
 * Tang Nano 9K BSRAM Bellek Haritasi:
 *   0x00000000 — Program belleginin baslangici (BSRAM, 64 KB)
 *   0x00008000 — Veri bolumunun baslangici    (BSRAM, 32 KB)
 *
 * NOT: data_base text_base'e yakin tutuldu; cunku Tang Nano 9K'da
 * PicoRV32 tek BSRAM blogu kullanir. 0x00010000 yerine 0x00008000.
 */

MEMORY {
    text_base = 0x00000000;   /* .text section baslangici (BSRAM) */
    data_base = 0x00008000;   /* .data section baslangici (BSRAM) */
}
