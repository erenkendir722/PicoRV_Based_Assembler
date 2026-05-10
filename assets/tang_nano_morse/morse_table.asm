# morse_table.asm — mesaj: "SOS"
.global MORSE_TABLE
.global MSG_TABLE

.data
.org 0x00000400

# Mors tablosu: A'dan Z'ye (26 harf x 4 byte = 104 byte)
# Format: ust byte = sembol sayisi, alt byte = pattern (bit0=ilk, 0=dit 1=dah)
MORSE_TABLE:
    .word 0x0202    # A  .-
    .word 0x0401    # B  -...
    .word 0x0405    # C  -.-.
    .word 0x0301    # D  -..
    .word 0x0100    # E  .
    .word 0x0404    # F  ..-.
    .word 0x0303    # G  --.
    .word 0x0400    # H  ....
    .word 0x0200    # I  ..
    .word 0x040E    # J  .---
    .word 0x0305    # K  -.-
    .word 0x0402    # L  .-..
    .word 0x0203    # M  --
    .word 0x0201    # N  -.
    .word 0x0307    # O  ---
    .word 0x0406    # P  .--.
    .word 0x040B    # Q  --.-
    .word 0x0302    # R  .-.
    .word 0x0300    # S  ...
    .word 0x0101    # T  -
    .word 0x0304    # U  ..-
    .word 0x0408    # V  ...-
    .word 0x0306    # W  .--
    .word 0x0409    # X  -..-
    .word 0x040D    # Y  -.--
    .word 0x0403    # Z  --..

# Mesaj: her karakter 1 word (ASCII), 0xFF ile biter
MSG_TABLE:
    .word 0x53      # 'S'
    .word 0x4F      # 'O'
    .word 0x53      # 'S'
    .word 0xFF      # bitis isaretcisi
