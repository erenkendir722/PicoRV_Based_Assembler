`timescale 1ns/1ps
// tb_reload.v — Reset ATMADAN ardisik iki program yukleme testi
// ─────────────────────────────────────────────────────────────────────
// Amac: Loader S_RUNNING'de iken host yeni yukleme (AA 55 ...) baslatinca
//       CPU'yu otomatik durdurup yeni programi kabul ettigini kanitlamak.
//       (S1 reset butonuna gerek kalmadan pes pese program yuklenebilir.)
//   1) test1_math yukle + RUN  -> sonuc 13
//   2) RESET YOK; test2_loop yukle + RUN -> sonuc 36
module tb_reload;
    localparam CLKS_PER_BIT = 8;
    localparam AWIDTH       = 11;

    reg clk = 0;
    always #5 clk = ~clk;

    reg        rst_btn = 1'b0;
    wire       uart_tx_pin;
    reg        uart_rx_pin = 1'b1;
    wire [5:0] led;

    top_loader #(.CLKS_PER_BIT(CLKS_PER_BIT), .AWIDTH(AWIDTH)) dut (
        .clk(clk), .rst_btn(rst_btn),
        .uart_rx(uart_rx_pin), .uart_tx(uart_tx_pin), .led(led)
    );

    localparam BIT_T = CLKS_PER_BIT * 10;

    task send_byte;
        input [7:0] b; integer i;
        begin
            uart_rx_pin = 0; #(BIT_T);
            for (i=0;i<8;i=i+1) begin uart_rx_pin=b[i]; #(BIT_T); end
            uart_rx_pin = 1; #(BIT_T);
            repeat(2) @(posedge clk);
        end
    endtask

    task recv_byte;
        output [7:0] b; integer k;
        begin
            @(negedge uart_tx_pin);
            #(BIT_T + BIT_T/2 + 5);
            for (k=0;k<8;k=k+1) begin b[k]=uart_tx_pin; #(BIT_T); end
        end
    endtask

    function [15:0] crc_next;
        input [15:0] c; input [7:0] d;
        reg [15:0] t; integer i;
        begin
            t = c ^ {d,8'h00};
            for (i=0;i<8;i=i+1) t = t[15] ? ((t<<1)^16'h1021) : (t<<1);
            crc_next = t;
        end
    endfunction

    reg [31:0] prog [0:2047];
    reg [15:0] crc;
    reg [7:0]  ack, result;
    integer    errors;
    reg [31:0] cw;

    task load_and_run;
        input [1023:0] path;
        input integer  nwords;
        integer wi, k, cnt;
        begin
            for (k=0;k<2048;k=k+1) prog[k]=0;
            $readmemh(path, prog);
            for (wi=0; wi<nwords; wi=wi+8) begin
                cnt = (nwords-wi < 8) ? (nwords-wi) : 8;
                crc = 16'hFFFF;
                send_byte(8'hAA); send_byte(8'h55);
                send_byte(8'h01);          crc=crc_next(crc,8'h01);
                send_byte((wi*4)>>24);     crc=crc_next(crc,(wi*4)>>24);
                send_byte((wi*4)>>16);     crc=crc_next(crc,(wi*4)>>16);
                send_byte((wi*4)>>8);      crc=crc_next(crc,(wi*4)>>8);
                send_byte((wi*4));         crc=crc_next(crc,(wi*4));
                send_byte(cnt[7:0]);       crc=crc_next(crc,cnt[7:0]);
                for (k=0;k<cnt;k=k+1) begin
                    cw = prog[wi+k];
                    send_byte(cw[31:24]); crc=crc_next(crc,cw[31:24]);
                    send_byte(cw[23:16]); crc=crc_next(crc,cw[23:16]);
                    send_byte(cw[15:8]);  crc=crc_next(crc,cw[15:8]);
                    send_byte(cw[7:0]);   crc=crc_next(crc,cw[7:0]);
                end
                send_byte(crc[15:8]); send_byte(crc[7:0]);
                recv_byte(ack);
                if (ack !== 8'h06) begin
                    $display("  [HATA] WRITE @%0d ACK yok (0x%02x)", wi*4, ack);
                    errors=errors+1;
                end
            end
            // RUN
            crc = crc_next(16'hFFFF, 8'h02);
            send_byte(8'hAA); send_byte(8'h55); send_byte(8'h02);
            send_byte(crc[15:8]); send_byte(crc[7:0]);
            recv_byte(ack);
            if (ack !== 8'h06) begin $display("  [HATA] RUN ACK yok"); errors=errors+1; end
        end
    endtask

    initial begin
        errors = 0;
        $dumpfile("tb_reload.vcd"); $dumpvars(0, tb_reload);
        $display("\n============================================================");
        $display(" RESET'SIZ ARDISIK YUKLEME TESTI");
        $display("============================================================");

        rst_btn=0; repeat(10) @(posedge clk);
        rst_btn=1; repeat(10) @(posedge clk);

        $display(" 1) test1_math yukle + RUN (beklenen 13):");
        load_and_run("../build/test1_math.words.hex", 11);
        recv_byte(result);
        $display("    -> CPU sonucu = %0d (0x%02x)", result, result);
        if (result !== 8'd13) begin $display("    [HATA] 13 degil!"); errors=errors+1; end

        $display(" 2) RESET YOK; test2_loop yukle + RUN (beklenen 36):");
        load_and_run("../build/test2_loop.words.hex", 14);
        recv_byte(result);
        $display("    -> CPU sonucu = %0d (0x%02x)", result, result);
        if (result !== 8'd36) begin $display("    [HATA] 36 degil!"); errors=errors+1; end

        $display("------------------------------------------------------------");
        if (errors==0)
            $display(" SONUC: GECTI — reset atmadan ikinci program yuklendi/calisti");
        else
            $display(" SONUC: KALDI (%0d hata)", errors);
        $display("============================================================\n");
        $finish;
    end

    initial #80_000_000 begin $display("HATA: WATCHDOG"); $finish; end
endmodule
