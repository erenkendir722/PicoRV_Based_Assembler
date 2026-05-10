.global MAIN
.text
.org 0x0

MAIN:
    lui  sp, 0x1        # sp = 0x1000

LOOP:
    # LED YAK: GPIO[0] = 1
    lui   x2, 0x2000    # x2 = 0x02000000
    addi  x3, x0, 1
    sw    x3, 0(x2)

    # BEKLE
    lui   x4, 0x32      # ~200ms @ 27MHz
WAIT1:
    addi  x4, x4, -1
    bne   x4, x0, WAIT1

    # LED SONDUR: GPIO[0] = 0
    lui   x2, 0x2000
    sw    x0, 0(x2)

    # BEKLE
    lui   x4, 0x32
WAIT2:
    addi  x4, x4, -1
    bne   x4, x0, WAIT2

    jal   x0, LOOP
