`timescale 1ns/1ps
// Basit smoke test: 4 word yükle, RUN gönder, CPU'nun cpu_run=1 yaptığını doğrula
module tb_loader;
    reg clk = 0;
    always #18 clk = ~clk;  // ~27 MHz

    reg  rst_btn = 0;
    wire uart_tx_pin;
    reg  uart_rx_pin = 1;
    wire [5:0] led;

    top_loader dut (
        .clk(clk), .rst_btn(rst_btn),
        .uart_rx(uart_rx_pin), .uart_tx(uart_tx_pin),
        .led(led)
    );

    // 115200 baud @ 27 MHz -> 234 saat
    localparam BIT_T = 234 * 36;  // ns

    task send_byte;
        input [7:0] b;
        integer i;
        begin
            uart_rx_pin = 0; #(BIT_T);
            for (i = 0; i < 8; i = i + 1) begin
                uart_rx_pin = b[i]; #(BIT_T);
            end
            uart_rx_pin = 1; #(BIT_T);
        end
    endtask

    function [15:0] crc16;
        input [15:0] c;
        input [7:0]  d;
        reg [15:0] t;
        integer i;
        begin
            t = c ^ {d, 8'h00};
            for (i = 0; i < 8; i = i + 1)
                t = t[15] ? ((t << 1) ^ 16'h1021) : (t << 1);
            crc16 = t;
        end
    endfunction

    reg [15:0] crc;
    integer j;

    task send_write;
        input [31:0] addr;
        input [31:0] w0, w1, w2, w3;
        begin
            crc = crc16(16'hFFFF, 8'h01);
            crc = crc16(crc, addr[31:24]);
            crc = crc16(crc, addr[23:16]);
            crc = crc16(crc, addr[15: 8]);
            crc = crc16(crc, addr[ 7: 0]);
            crc = crc16(crc, 8'h04);
            crc = crc16(crc, w0[31:24]); crc = crc16(crc, w0[23:16]);
            crc = crc16(crc, w0[15: 8]); crc = crc16(crc, w0[ 7: 0]);
            crc = crc16(crc, w1[31:24]); crc = crc16(crc, w1[23:16]);
            crc = crc16(crc, w1[15: 8]); crc = crc16(crc, w1[ 7: 0]);
            crc = crc16(crc, w2[31:24]); crc = crc16(crc, w2[23:16]);
            crc = crc16(crc, w2[15: 8]); crc = crc16(crc, w2[ 7: 0]);
            crc = crc16(crc, w3[31:24]); crc = crc16(crc, w3[23:16]);
            crc = crc16(crc, w3[15: 8]); crc = crc16(crc, w3[ 7: 0]);

            send_byte(8'hAA); send_byte(8'h55); send_byte(8'h01);
            send_byte(addr[31:24]); send_byte(addr[23:16]);
            send_byte(addr[15: 8]); send_byte(addr[ 7: 0]);
            send_byte(8'h04);
            send_byte(w0[31:24]); send_byte(w0[23:16]);
            send_byte(w0[15: 8]); send_byte(w0[ 7: 0]);
            send_byte(w1[31:24]); send_byte(w1[23:16]);
            send_byte(w1[15: 8]); send_byte(w1[ 7: 0]);
            send_byte(w2[31:24]); send_byte(w2[23:16]);
            send_byte(w2[15: 8]); send_byte(w2[ 7: 0]);
            send_byte(w3[31:24]); send_byte(w3[23:16]);
            send_byte(w3[15: 8]); send_byte(w3[ 7: 0]);
            send_byte(crc[15:8]); send_byte(crc[7:0]);
            #(BIT_T * 12);  // ACK bekleme
        end
    endtask

    task send_run;
        begin
            crc = crc16(16'hFFFF, 8'h02);
            send_byte(8'hAA); send_byte(8'h55); send_byte(8'h02);
            send_byte(crc[15:8]); send_byte(crc[7:0]);
            #(BIT_T * 12);
        end
    endtask

    initial begin
        #100 rst_btn = 1;
        #500;
        send_write(32'h0, 32'h00000013, 32'h00000013, 32'h00000013, 32'h00000013);
        send_run();
        #(BIT_T * 20);
        if (dut.cpu_run)
            $display("SONUC: GECTI — cpu_run=1");
        else
            $display("SONUC: BASARISIZ — cpu_run=0");
        $finish;
    end

    initial #50000000 begin $display("TIMEOUT"); $finish; end
endmodule
