`timescale 1ns/1ps
// tb_loader.v — Genel loader testbench
// Kullanim: vvp sim.out +PROG=<path.words.hex> +WORDS=<n> +EXP=<beklenen_deger>
// Hiz: CLKS_PER_BIT=8 (simulasyonu hizlandirir), gercek 234 degil
module tb_loader;
    localparam CLKS_PER_BIT = 8;
    localparam AWIDTH       = 11;

    reg clk = 0;
    always #5 clk = ~clk;  // 10 ns periyot

    reg        rst_btn = 1'b0;
    wire       uart_tx_pin;
    reg        uart_rx_pin = 1'b1;
    wire [5:0] led;

    top_loader #(.CLKS_PER_BIT(CLKS_PER_BIT), .AWIDTH(AWIDTH)) dut (
        .clk(clk), .rst_btn(rst_btn),
        .uart_rx(uart_rx_pin), .uart_tx(uart_tx_pin),
        .led(led)
    );

    localparam BIT_T = CLKS_PER_BIT * 10;  // ns (10 ns/clk)

    // ── UART gonderici gorev ─────────────────────────────────────────────
    task send_byte;
        input [7:0] b;
        integer i;
        begin
            uart_rx_pin = 0; #(BIT_T);
            for (i = 0; i < 8; i = i + 1) begin
                uart_rx_pin = b[i]; #(BIT_T);
            end
            uart_rx_pin = 1; #(BIT_T);
            repeat(2) @(posedge clk);
        end
    endtask

    // ── UART alici gorev ─────────────────────────────────────────────────
    task recv_byte;
        output [7:0] b;
        integer k;
        begin
            @(negedge uart_tx_pin);  // start bit
            // uart_tx.v: start bit 9 clk, bit0 orta = 9 + CLKS_PER_BIT/2
            repeat(CLKS_PER_BIT + CLKS_PER_BIT/2 + 1) @(posedge clk);
            for (k = 0; k < 8; k = k + 1) begin
                b[k] = uart_tx_pin;
                repeat(CLKS_PER_BIT) @(posedge clk);
            end
        end
    endtask

    // ── CRC-16/CCITT-FALSE ───────────────────────────────────────────────
    function [15:0] crc_next;
        input [15:0] c;
        input [7:0]  d;
        reg [15:0] t;
        integer i;
        begin
            t = c ^ {d, 8'h00};
            for (i = 0; i < 8; i = i + 1)
                t = t[15] ? ((t << 1) ^ 16'h1021) : (t << 1);
            crc_next = t;
        end
    endfunction

    // ── Program bellegi ──────────────────────────────────────────────────
    reg [31:0] prog [0:2047];
    integer    total_words;
    integer    exp_val;
    reg [7:0]  result;
    integer    errors;
    integer    pk, w, pw;
    reg [15:0] crc;
    reg [7:0]  ack;
    reg [31:0] cur_word;

    localparam CHUNK = 8;  // paket basina word

    // ── WRITE paketi gonderici ───────────────────────────────────────────
    task send_write_chunk;
        input [31:0] base_addr;
        input integer start_w;
        input integer cnt;
        integer k;
        reg [7:0] ack_byte;
        begin
            crc = 16'hFFFF;
            send_byte(8'hAA); send_byte(8'h55);
            send_byte(8'h01);           crc = crc_next(crc, 8'h01);
            send_byte(base_addr[31:24]); crc = crc_next(crc, base_addr[31:24]);
            send_byte(base_addr[23:16]); crc = crc_next(crc, base_addr[23:16]);
            send_byte(base_addr[15:8]);  crc = crc_next(crc, base_addr[15:8]);
            send_byte(base_addr[7:0]);   crc = crc_next(crc, base_addr[7:0]);
            send_byte(cnt[7:0]);         crc = crc_next(crc, cnt[7:0]);
            for (k = 0; k < cnt; k = k + 1) begin
                cur_word = prog[start_w + k];
                send_byte(cur_word[31:24]); crc = crc_next(crc, cur_word[31:24]);
                send_byte(cur_word[23:16]); crc = crc_next(crc, cur_word[23:16]);
                send_byte(cur_word[15:8]);  crc = crc_next(crc, cur_word[15:8]);
                send_byte(cur_word[7:0]);   crc = crc_next(crc, cur_word[7:0]);
            end
            send_byte(crc[15:8]); send_byte(crc[7:0]);
            recv_byte(ack_byte);
            if (ack_byte !== 8'h06) begin
                $display("  [HATA] WRITE @0x%08x ACK beklendi, 0x%02x geldi", base_addr, ack_byte);
                errors = errors + 1;
            end else
                $display("  [OK]   WRITE @0x%08x %0d word -> ACK", base_addr, cnt);
        end
    endtask

    // ── RUN paketi ───────────────────────────────────────────────────────
    task send_run;
        reg [7:0] ack_byte;
        begin
            crc = crc_next(16'hFFFF, 8'h02);
            send_byte(8'hAA); send_byte(8'h55); send_byte(8'h02);
            send_byte(crc[15:8]); send_byte(crc[7:0]);
            recv_byte(ack_byte);
            if (ack_byte !== 8'h06) begin
                $display("  [HATA] RUN ACK beklendi, 0x%02x geldi", ack_byte);
                errors = errors + 1;
            end else
                $display("  [OK]   RUN -> ACK");
        end
    endtask

    // ── Ana test akisi ───────────────────────────────────────────────────
    reg [1023:0] prog_path;
    integer      chunk_cnt;

    initial begin
        errors = 0;

        if (!$value$plusargs("PROG=%s",  prog_path))  prog_path  = "../build/test1_math.words.hex";
        if (!$value$plusargs("WORDS=%d", total_words)) total_words = 11;
        if (!$value$plusargs("EXP=%d",   exp_val))    exp_val    = 13;

        $dumpfile("tb_loader.vcd"); $dumpvars(0, tb_loader);

        // BRAM'i sifirla ve programi yukle
        begin : init_mem
            integer i;
            for (i = 0; i < 2048; i = i + 1) prog[i] = 32'h0;
        end
        $readmemh(prog_path, prog);

        $display("\n============================================================");
        $display(" LOADER TESTI  prog=%0s  words=%0d  beklenen=%0d",
                 prog_path, total_words, exp_val);
        $display("============================================================");

        rst_btn = 0; repeat(10) @(posedge clk);
        rst_btn = 1; repeat(10) @(posedge clk);

        // Paketi CHUNK'lar halinde gonder
        begin : load_loop
            integer wi;
            for (wi = 0; wi < total_words; wi = wi + CHUNK) begin
                chunk_cnt = (total_words - wi < CHUNK) ? (total_words - wi) : CHUNK;
                send_write_chunk(wi * 4, wi, chunk_cnt);
            end
        end

        send_run();

        // CPU'nun UART'tan dondurecegi sonucu oku
        recv_byte(result);
        $display("  [<-]  CPU UART sonucu = %0d (0x%02x)  LED = %b",
                 result, result, led);

        if (result !== exp_val[7:0]) begin
            $display("  [HATA] Beklenen %0d, gelen %0d", exp_val, result);
            errors = errors + 1;
        end

        $display("------------------------------------------------------------");
        if (errors == 0)
            $display(" SONUC: GECTI");
        else
            $display(" SONUC: KALDI (%0d hata)", errors);
        $display("============================================================\n");
        $finish;
    end

    initial #50_000_000 begin $display("HATA: WATCHDOG zaman asimi!"); $finish; end
endmodule
