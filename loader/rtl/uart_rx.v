// ════════════════════════════════════════════════════════════════════
// uart_rx.v — UART Alici (8N1)
// ════════════════════════════════════════════════════════════════════
// Bilgisayardan (host) FPGA'e gelen seri veriyi paralel bayta cevirir.
// 8 veri biti, parite yok, 1 stop biti (8N1).
//
// CLKS_PER_BIT = (saat frekansi) / (baud hizi)
//   ornek: 27 MHz / 115200 baud ≈ 234
//
// Literatur: standart oversampling-tabanli UART RX (Nandland tarzi),
// gomulu sistemlerde yaygin kullanilan referans tasarim [bkz. rapor 1.2].
//
// Cikis protokolu:
//   o_valid bir saat darbesi boyunca '1' olur ve o anda o_data gecerlidir.
// ════════════════════════════════════════════════════════════════════
module uart_rx #(
    parameter CLKS_PER_BIT = 234
)(
    input  wire       clk,
    input  wire       rst_n,
    input  wire       i_rx,        // seri giris (host -> fpga)
    output reg        o_valid,     // 1 darbe: yeni bayt hazir
    output reg [7:0]  o_data       // alinan bayt
);

    localparam S_IDLE  = 3'd0;
    localparam S_START = 3'd1;
    localparam S_DATA  = 3'd2;
    localparam S_STOP  = 3'd3;
    localparam S_CLEAN = 3'd4;

    reg [2:0]  state;
    reg [15:0] clk_cnt;
    reg [2:0]  bit_idx;
    reg [7:0]  shifter;

    // ── Iki-asamali senkronizer (metastabilite onleme) ──────────────
    reg rx_d1, rx_d2;
    always @(posedge clk) begin
        rx_d1 <= i_rx;
        rx_d2 <= rx_d1;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state   <= S_IDLE;
            clk_cnt <= 0;
            bit_idx <= 0;
            shifter <= 0;
            o_valid <= 0;
            o_data  <= 0;
        end else begin
            o_valid <= 0;   // varsayilan: sadece 1 darbe

            case (state)
                // ── Bosta: start biti (0) bekle ──────────────────────
                S_IDLE: begin
                    clk_cnt <= 0;
                    bit_idx <= 0;
                    if (rx_d2 == 1'b0)      // dusen kenar = start
                        state <= S_START;
                end

                // ── Start bitinin ortasinda dogrula ──────────────────
                S_START: begin
                    if (clk_cnt == (CLKS_PER_BIT-1)/2) begin
                        if (rx_d2 == 1'b0) begin
                            clk_cnt <= 0;
                            state   <= S_DATA;
                        end else
                            state <= S_IDLE;   // gecersiz start
                    end else
                        clk_cnt <= clk_cnt + 1'b1;
                end

                // ── 8 veri bitini orta-bit'te ornekle (LSB once) ─────
                S_DATA: begin
                    if (clk_cnt == CLKS_PER_BIT-1) begin
                        clk_cnt          <= 0;
                        shifter[bit_idx] <= rx_d2;
                        if (bit_idx == 3'd7) begin
                            bit_idx <= 0;
                            state   <= S_STOP;
                        end else
                            bit_idx <= bit_idx + 1'b1;
                    end else
                        clk_cnt <= clk_cnt + 1'b1;
                end

                // ── Stop biti ────────────────────────────────────────
                S_STOP: begin
                    if (clk_cnt == CLKS_PER_BIT-1) begin
                        o_data  <= shifter;
                        o_valid <= 1'b1;
                        clk_cnt <= 0;
                        state   <= S_CLEAN;
                    end else
                        clk_cnt <= clk_cnt + 1'b1;
                end

                // ── Hat bosa donsun (cift tetiklemeyi onle) ──────────
                S_CLEAN: begin
                    if (rx_d2 == 1'b1)
                        state <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
