// ════════════════════════════════════════════════════════════════════
// tb_loader.v — Loader Zinciri icin Self-Checking Testbench
// ════════════════════════════════════════════════════════════════════
// Tum yukleme zincirini SIMULASYONDA dogrular:
//   host(TB) --UART--> uart_rx --> loader --> BRAM --> CPU --> uart_tx --> host(TB)
//
// Akis:
//   1) Program word'leri +PROG=<dosya>.words.hex'ten okunur.
//   2) WRITE paketleri (8 word/paket) CRC ile gonderilir; her paket icin
//      FPGA'den ACK(0x06) beklenir.
//   3) RUN paketi gonderilir; ACK beklenir; CPU calismaya baslar.
//   4) CPU sonucu UART'tan geri gonderir; TB bunu yakalayip +EXP ile karsilastirir.
//   5) Ayrica dut.led_reg (LED ciktisi) beklenen sonuca esit mi kontrol edilir.
//
// Calistirma (run.sh halleder):
//   vvp sim.out +PROG=../build/test1_math.words.hex +WORDS=11 +EXP=13
// ════════════════════════════════════════════════════════════════════
`timescale 1ns/1ps
`default_nettype none

module tb_loader;

    localparam CLKS_PER_BIT = 8;        // hizli sim icin kucuk baud bolen
    localparam AWIDTH       = 11;

    // ── Saat ─────────────────────────────────────────────────────────
    reg clk = 0;
    always #5 clk = ~clk;               // 100 MHz sim saati (periyot 10 ns)

    // ── DUT baglantilari ─────────────────────────────────────────────
    reg        rst_btn = 1'b0;          // active-low: 0 = reset
    reg        uart_rx = 1'b1;          // bosta yuksek
    wire       uart_tx;
    wire [5:0] led;

    top_loader #(.CLKS_PER_BIT(CLKS_PER_BIT), .AWIDTH(AWIDTH)) dut (
        .clk(clk), .rst_btn(rst_btn),
        .uart_rx(uart_rx), .uart_tx(uart_tx), .led(led)
    );

    // ── Program belle ────────────────────────────────────────────────
    reg [31:0] prog [0:1023];
    reg [8*128:1] prog_file;
    integer prog_words;
    integer exp_result;

    integer i, errors;
    reg [7:0] rb;

    // ── CRC-16/CCITT-FALSE (loader.v ile birebir) ───────────────────
    function [15:0] crc_next;
        input [15:0] c_in;
        input [7:0]  d;
        reg   [15:0] c;
        integer j;
        begin
            c = c_in ^ {d, 8'h00};
            for (j = 0; j < 8; j = j + 1)
                c = c[15] ? ((c << 1) ^ 16'h1021) : (c << 1);
            crc_next = c;
        end
    endfunction

    // ── UART gonder (TB -> FPGA), 1 bayt, 8N1 ───────────────────────
    task uart_send;
        input [7:0] b;
        integer k;
        begin
            uart_rx = 1'b0;                                   // start
            repeat (CLKS_PER_BIT) @(posedge clk);
            for (k = 0; k < 8; k = k + 1) begin
                uart_rx = b[k];                               // LSB once
                repeat (CLKS_PER_BIT) @(posedge clk);
            end
            uart_rx = 1'b1;                                   // stop
            repeat (CLKS_PER_BIT) @(posedge clk);
            repeat (2) @(posedge clk);                        // baytlar arasi bosluk
        end
    endtask

    // ── UART al (FPGA -> TB), 1 bayt, 8N1 ───────────────────────────
    task uart_recv;
        output [7:0] b;
        integer k;
        begin
            @(negedge uart_tx);                               // start biti
            repeat (CLKS_PER_BIT + CLKS_PER_BIT/2) @(posedge clk);  // ilk veri bitinin ortasi
            for (k = 0; k < 8; k = k + 1) begin
                b[k] = uart_tx;
                repeat (CLKS_PER_BIT) @(posedge clk);
            end
            // stop bitini beklemeye gerek yok
        end
    endtask

    // ── WRITE paketi gonder: prog[start .. start+cnt-1] ─────────────
    task send_write;
        input [31:0] base;        // bayt adresi
        input integer start_word;
        input integer cnt;
        integer k;
        reg [15:0] crc;
        reg [31:0] w;
        reg [7:0] ack;
        begin
            // header + CRC hesabi
            crc = 16'hFFFF;
            uart_send(8'hAA);
            uart_send(8'h55);
            uart_send(8'h01);                 crc = crc_next(crc, 8'h01);
            uart_send(base[31:24]);           crc = crc_next(crc, base[31:24]);
            uart_send(base[23:16]);           crc = crc_next(crc, base[23:16]);
            uart_send(base[15:8]);            crc = crc_next(crc, base[15:8]);
            uart_send(base[7:0]);             crc = crc_next(crc, base[7:0]);
            uart_send(cnt[7:0]);              crc = crc_next(crc, cnt[7:0]);
            for (k = 0; k < cnt; k = k + 1) begin
                w = prog[start_word + k];
                uart_send(w[31:24]);          crc = crc_next(crc, w[31:24]);
                uart_send(w[23:16]);          crc = crc_next(crc, w[23:16]);
                uart_send(w[15:8]);           crc = crc_next(crc, w[15:8]);
                uart_send(w[7:0]);            crc = crc_next(crc, w[7:0]);
            end
            uart_send(crc[15:8]);
            uart_send(crc[7:0]);
            // ACK bekle
            uart_recv(ack);
            if (ack !== 8'h06) begin
                $display("  [HATA] WRITE @0x%08x x%0d -> ACK degil (0x%02x)", base, cnt, ack);
                errors = errors + 1;
            end else
                $display("  [OK]   WRITE @0x%08x  %0d word -> ACK", base, cnt);
        end
    endtask

    // ── RUN paketi gonder ────────────────────────────────────────────
    task send_run;
        reg [15:0] crc;
        reg [7:0] ack;
        begin
            crc = 16'hFFFF;
            uart_send(8'hAA);
            uart_send(8'h55);
            uart_send(8'h02);   crc = crc_next(crc, 8'h02);
            uart_send(crc[15:8]);
            uart_send(crc[7:0]);
            uart_recv(ack);
            if (ack !== 8'h06) begin
                $display("  [HATA] RUN -> ACK degil (0x%02x)", ack);
                errors = errors + 1;
            end else
                $display("  [OK]   RUN -> ACK  (CPU reset serbest birakildi)");
        end
    endtask

    // ── Ana senaryo ──────────────────────────────────────────────────
    integer base_word, chunk;
    initial begin
        errors = 0;
        // VCD dalga formu (gtkwave / demo icin)
        $dumpfile("tb_loader.vcd");
        $dumpvars(0, tb_loader);

        // Argumanlar
        if (!$value$plusargs("PROG=%s", prog_file)) begin
            $display("HATA: +PROG=<dosya> verilmedi"); $finish;
        end
        if (!$value$plusargs("WORDS=%d", prog_words)) prog_words = 0;
        if (!$value$plusargs("EXP=%d",  exp_result))  exp_result = -1;

        for (i = 0; i < 1024; i = i + 1) prog[i] = 32'h0;
        $readmemh(prog_file, prog);

        $display("\n============================================================");
        $display(" LOADER SIM  |  program=%0s  words=%0d  beklenen sonuc=%0d",
                 prog_file, prog_words, exp_result);
        $display("============================================================");

        // Reset (active-low) birakma
        rst_btn = 1'b0;
        repeat (10) @(posedge clk);
        rst_btn = 1'b1;
        repeat (10) @(posedge clk);

        // ── WRITE paketleri (8 word/paket) ──────────────────────────
        chunk = 8;
        base_word = 0;
        while (base_word < prog_words) begin
            if (base_word + chunk <= prog_words)
                send_write(base_word*4, base_word, chunk);
            else
                send_write(base_word*4, base_word, prog_words - base_word);
            base_word = base_word + chunk;
        end

        // ── RUN ─────────────────────────────────────────────────────
        send_run;

        // ── Programin UART'tan gonderdigi sonuc baytini yakala ──────
        uart_recv(rb);
        $display("  [<-]   CPU UART sonucu = %0d (0x%02x)", rb, rb);
        if (exp_result >= 0 && rb !== exp_result[7:0]) begin
            $display("  [HATA] UART sonuc beklenenden farkli! (beklenen %0d)", exp_result);
            errors = errors + 1;
        end

        // ── LED register'i kontrol et ───────────────────────────────
        repeat (20) @(posedge clk);
        $display("  [LED]  led_reg = %0d (0b%06b)  | LED pinleri = 0b%06b (aktif-dusuk)",
                 dut.led_reg, dut.led_reg, led);
        if (exp_result >= 0 && dut.led_reg !== exp_result[5:0]) begin
            $display("  [HATA] LED register beklenenden farkli!");
            errors = errors + 1;
        end

        $display("------------------------------------------------------------");
        if (errors == 0)
            $display(" SONUC: GECTI (tum kontroller basarili)");
        else
            $display(" SONUC: KALDI (%0d hata)", errors);
        $display("============================================================\n");
        $finish;
    end

    // ── Watchdog ─────────────────────────────────────────────────────
    initial begin
        #5000000;   // 5 ms sim guvenlik siniri
        $display("HATA: WATCHDOG zaman asimi! (sim takildi)");
        $finish;
    end

endmodule

`default_nettype wire
