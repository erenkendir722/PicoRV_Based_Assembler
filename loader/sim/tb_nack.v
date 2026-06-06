// ════════════════════════════════════════════════════════════════════
// tb_nack.v — CRC Hata Kontrolu / NACK + Yeniden Gonderim Testi
// ════════════════════════════════════════════════════════════════════
// Amac: Loader'in BOZUK bir paketi CRC ile yakalayip NACK (0x15) ile
// reddettigini ve dogru paket tekrar gonderilince ACK (0x06) verip
// programi sorunsuz calistirdigini kanitlamak.
//
//   1) WRITE paketi BOZUK CRC ile gonderilir   -> NACK beklenir
//   2) Ayni paket DOGRU CRC ile tekrar gonderilir -> ACK beklenir
//   3) Kalan paket + RUN -> program calisir -> sonuc 13 dogrulanir
//
// Program: test1_math (6 + 7 = 13)
// ════════════════════════════════════════════════════════════════════
`timescale 1ns/1ps
`default_nettype none

module tb_nack;
    localparam CLKS_PER_BIT = 8;
    localparam AWIDTH       = 11;

    reg clk = 0;
    always #5 clk = ~clk;  // 10 ns periyot

    reg        rst_btn = 1'b0;
    reg        uart_rx = 1'b1;
    wire       uart_tx;
    wire [5:0] led;

    top_loader #(.CLKS_PER_BIT(CLKS_PER_BIT), .AWIDTH(AWIDTH)) dut (
        .clk(clk), .rst_btn(rst_btn),
        .uart_rx(uart_rx), .uart_tx(uart_tx), .led(led)
    );

    reg [31:0] prog [0:1023];
    integer errors;

    // ── CRC-16/CCITT-FALSE ───────────────────────────────────────────────
    function [15:0] crc_next;
        input [15:0] c_in; input [7:0] d;
        reg [15:0] c; integer j;
        begin
            c = c_in ^ {d, 8'h00};
            for (j=0;j<8;j=j+1) c = c[15] ? ((c<<1)^16'h1021) : (c<<1);
            crc_next = c;
        end
    endfunction

    // BIT_T: 1 bit suresi ns cinsinden (CLKS_PER_BIT * 10ns/clk)
    localparam BIT_T = CLKS_PER_BIT * 10;

    // ── UART gonderici ───────────────────────────────────────────────────
    task uart_send;
        input [7:0] b; integer k;
        begin
            uart_rx = 0; #(BIT_T);
            for (k=0;k<8;k=k+1) begin uart_rx=b[k]; #(BIT_T); end
            uart_rx = 1; #(BIT_T);
            repeat(2) @(posedge clk);  // tb_loader ile ayni guard
        end
    endtask

    // ── UART alici ───────────────────────────────────────────────────────
    task uart_recv;
        output [7:0] b; integer k;
        begin
            @(negedge uart_tx);
            // uart_tx.v: start bit 9 clk, bit0 orta = 9 + CLKS_PER_BIT/2
            #(BIT_T + BIT_T/2 + 5);  // 1.5 bit + kucuk marj (ns)
            for (k=0;k<8;k=k+1) begin
                b[k] = uart_tx;
                #(BIT_T);
            end
        end
    endtask

    // ── WRITE paketi ─────────────────────────────────────────────────────
    task send_write;
        input [31:0] base; input integer sw; input integer cnt; input corrupt;
        integer k; reg [15:0] crc; reg [31:0] w; reg [7:0] ack;
        begin
            crc = 16'hFFFF;
            uart_send(8'hAA); uart_send(8'h55);
            uart_send(8'h01);          crc = crc_next(crc, 8'h01);
            uart_send(base[31:24]);    crc = crc_next(crc, base[31:24]);
            uart_send(base[23:16]);    crc = crc_next(crc, base[23:16]);
            uart_send(base[15:8]);     crc = crc_next(crc, base[15:8]);
            uart_send(base[7:0]);      crc = crc_next(crc, base[7:0]);
            uart_send(cnt[7:0]);       crc = crc_next(crc, cnt[7:0]);
            for (k=0;k<cnt;k=k+1) begin
                w = prog[sw+k];
                uart_send(w[31:24]);   crc = crc_next(crc, w[31:24]);
                uart_send(w[23:16]);   crc = crc_next(crc, w[23:16]);
                uart_send(w[15:8]);    crc = crc_next(crc, w[15:8]);
                uart_send(w[7:0]);     crc = crc_next(crc, w[7:0]);
            end
            if (corrupt) crc = crc ^ 16'hBEEF;
            uart_send(crc[15:8]); uart_send(crc[7:0]);
            uart_recv(ack);
            if (corrupt) begin
                if (ack === 8'h15) $display("  [OK]   Bozuk paket -> NACK (0x15) dogru reddedildi");
                else begin $display("  [HATA] Bozuk paket NACK ile reddedilmedi! (0x%02x)", ack); errors=errors+1; end
            end else begin
                if (ack === 8'h06) $display("  [OK]   WRITE @0x%08x %0d word -> ACK", base, cnt);
                else begin $display("  [HATA] Dogru paket ACK alamadi! (0x%02x)", ack); errors=errors+1; end
            end
        end
    endtask

    task send_run;
        reg [15:0] crc; reg [7:0] ack;
        begin
            crc = crc_next(16'hFFFF, 8'h02);
            uart_send(8'hAA); uart_send(8'h55); uart_send(8'h02);
            uart_send(crc[15:8]); uart_send(crc[7:0]);
            uart_recv(ack);
            if (ack===8'h06) $display("  [OK]   RUN -> ACK");
            else begin $display("  [HATA] RUN ACK yok (0x%02x)", ack); errors=errors+1; end
        end
    endtask

    // ── Ana test ─────────────────────────────────────────────────────────
    integer i;
    reg [7:0] rb;

    initial begin
        errors = 0;
        $dumpfile("tb_nack.vcd"); $dumpvars(0, tb_nack);
        for (i=0;i<1024;i=i+1) prog[i]=0;
        $readmemh("../build/test1_math.words.hex", prog);

        $display("\n============================================================");
        $display(" NACK / CRC HATA KONTROLU TESTI  (test1_math, sonuc=13)");
        $display("============================================================");

        rst_btn=0; repeat(10) @(posedge clk);
        rst_btn=1; repeat(10) @(posedge clk);

        $display(" 1) Ilk paketi BOZUK CRC ile gonder:");
        send_write(32'h0, 0, 8, 1'b1);      // corrupt -> NACK
        $display(" 2) Ayni paketi DOGRU CRC ile tekrar gonder:");
        send_write(32'h0, 0, 8, 1'b0);      // dogru -> ACK
        $display(" 3) Kalan paket + RUN:");
        send_write(32'h20, 8, 3, 1'b0);
        send_run;

        uart_recv(rb);
        $display("  [<-]   CPU UART sonucu = %0d (0x%02x)", rb, rb);
        if (rb !== 8'd13) begin $display("  [HATA] sonuc 13 degil!"); errors=errors+1; end

        $display("------------------------------------------------------------");
        if (errors==0) $display(" SONUC: GECTI — CRC bozuk paketi reddetti, tekrar gonderim calisti");
        else           $display(" SONUC: KALDI (%0d hata)", errors);
        $display("============================================================\n");
        $finish;
    end

    initial begin #50_000_000; $display("HATA: WATCHDOG zaman asimi!"); $finish; end
endmodule
`default_nettype wire
