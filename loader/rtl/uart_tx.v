// ════════════════════════════════════════════════════════════════════
// uart_tx.v — UART Gonderici (8N1)
// ════════════════════════════════════════════════════════════════════
// FPGA'den bilgisayara (host) bayt gonderir. Loader bunu ACK/NACK
// gondermek icin, calisan program ise sonuc baytini gondermek icin
// kullanir (UART hatti loader ile CPU arasinda top_loader.v'de paylasilir).
//
//   i_start : 1 darbe -> i_data gonderilmeye baslar
//   o_busy  : gonderim suresince '1' (yeni i_start yok sayilir)
//   o_tx    : seri cikis (fpga -> host), bosta '1'
// ════════════════════════════════════════════════════════════════════
module uart_tx #(
    parameter CLKS_PER_BIT = 234
)(
    input  wire       clk,
    input  wire       rst_n,
    input  wire       i_start,
    input  wire [7:0] i_data,
    output reg        o_tx,
    output reg        o_busy
);

    localparam S_IDLE  = 2'd0;
    localparam S_START = 2'd1;
    localparam S_DATA  = 2'd2;
    localparam S_STOP  = 2'd3;

    reg [1:0]  state;
    reg [15:0] clk_cnt;
    reg [2:0]  bit_idx;
    reg [7:0]  shifter;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state   <= S_IDLE;
            clk_cnt <= 0;
            bit_idx <= 0;
            shifter <= 0;
            o_tx    <= 1'b1;   // bosta hat yuksek
            o_busy  <= 1'b0;
        end else begin
            case (state)
                // ── Bosta: start tetigi bekle ────────────────────────
                S_IDLE: begin
                    o_tx    <= 1'b1;
                    clk_cnt <= 0;
                    bit_idx <= 0;
                    if (i_start) begin
                        shifter <= i_data;
                        o_busy  <= 1'b1;
                        o_tx    <= 1'b0;   // start biti
                        state   <= S_START;
                    end else
                        o_busy <= 1'b0;
                end

                // ── Start biti suresi ────────────────────────────────
                S_START: begin
                    if (clk_cnt == CLKS_PER_BIT-1) begin
                        clk_cnt <= 0;
                        o_tx    <= shifter[0];
                        state   <= S_DATA;
                    end else
                        clk_cnt <= clk_cnt + 1'b1;
                end

                // ── 8 veri biti (LSB once) ───────────────────────────
                S_DATA: begin
                    if (clk_cnt == CLKS_PER_BIT-1) begin
                        clk_cnt <= 0;
                        if (bit_idx == 3'd7) begin
                            bit_idx <= 0;
                            o_tx    <= 1'b1;   // stop biti
                            state   <= S_STOP;
                        end else begin
                            bit_idx <= bit_idx + 1'b1;
                            o_tx    <= shifter[bit_idx + 1'b1];
                        end
                    end else
                        clk_cnt <= clk_cnt + 1'b1;
                end

                // ── Stop biti ────────────────────────────────────────
                S_STOP: begin
                    if (clk_cnt == CLKS_PER_BIT-1) begin
                        clk_cnt <= 0;
                        o_busy  <= 1'b0;
                        state   <= S_IDLE;
                    end else
                        clk_cnt <= clk_cnt + 1'b1;
                end

                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
