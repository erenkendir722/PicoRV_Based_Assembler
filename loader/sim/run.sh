#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════
# run.sh — Loader zincirini Icarus Verilog ile derle + testleri calistir
# ════════════════════════════════════════════════════════════════════
# Onkosul:  iverilog + vvp kurulu olmali  (brew install icarus-verilog)
#           python3 loader/host/build_tests.py  ile ciktilar uretilmis olmali
# ════════════════════════════════════════════════════════════════════
set -e
cd "$(dirname "$0")"

RTL=../rtl
BUILD=../build
TB_OUT=tb_loader.out
NACK_OUT=nack.out

SOURCES=(
    "$RTL/top_loader.v"
    "$RTL/uart_rx.v"
    "$RTL/uart_tx.v"
    "$RTL/loader.v"
    "$RTL/bram_mem.v"
    "$RTL/picorv32.v"
)

echo "=== Derleme: tb_loader (iverilog) ==="
iverilog -g2012 -o "$TB_OUT" tb_loader.v "${SOURCES[@]}"
echo "Derleme OK -> $TB_OUT"
echo

# Test adi : word sayisi : beklenen sonuc
run_test () {
    local name="$1" words="$2" exp="$3"
    echo "########################################################"
    echo "# $name  (words=$words, beklenen=$exp)"
    echo "########################################################"
    vvp "$TB_OUT" \
        +PROG="$BUILD/$name.words.hex" \
        +WORDS="$words" \
        +EXP="$exp"
    [ -f tb_loader.vcd ] && mv -f tb_loader.vcd "$name.vcd"
    echo
}

run_test test1_math 11 13
run_test test2_loop 14 36
run_test test3_func 38 55

echo "########################################################"
echo "# tb_nack — CRC hata kontrolu / NACK + yeniden gonderim"
echo "########################################################"
iverilog -g2012 -o "$NACK_OUT" tb_nack.v "${SOURCES[@]}"
vvp "$NACK_OUT"
echo

echo "Tum testler tamamlandi."
