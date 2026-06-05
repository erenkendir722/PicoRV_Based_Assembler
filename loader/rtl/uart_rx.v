// uart_rx.v — 8N1 UART alici
// 27 MHz saat, 115200 baud -> CLKS_PER_BIT = 234
module uart_rx #(
    parameter CLKS_PER_BIT = 234
)(
    input  wire       clk,
    input  wire       rst_n,
    input  wire       rx,
    output reg        valid,   // 1 darbe: yeni bayt hazir
    output reg  [7:0] data
);
    localparam S_IDLE  = 2'd0;
    localparam S_START = 2'd1;
    localparam S_DATA  = 2'd2;
    localparam S_STOP  = 2'd3;

    reg [1:0]  state = S_IDLE;
    reg [8:0]  cnt   = 0;
    reg [2:0]  bit_i = 0;
    reg [7:0]  shift = 0;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE; valid <= 0; cnt <= 0;
        end else begin
            valid <= 0;
            case (state)
                S_IDLE:
                    if (!rx) begin
                        cnt   <= CLKS_PER_BIT / 2;
                        state <= S_START;
                    end
                S_START:
                    if (cnt == 0) begin
                        if (!rx) begin
                            cnt   <= CLKS_PER_BIT - 1;
                            bit_i <= 0;
                            state <= S_DATA;
                        end else
                            state <= S_IDLE;
                    end else
                        cnt <= cnt - 1;
                S_DATA:
                    if (cnt == 0) begin
                        shift <= {rx, shift[7:1]};
                        cnt   <= CLKS_PER_BIT - 1;
                        if (bit_i == 7)
                            state <= S_STOP;
                        else
                            bit_i <= bit_i + 1;
                    end else
                        cnt <= cnt - 1;
                S_STOP:
                    if (cnt == 0) begin
                        if (rx) begin
                            data  <= shift;
                            valid <= 1;
                        end
                        state <= S_IDLE;
                    end else
                        cnt <= cnt - 1;
            endcase
        end
    end
endmodule
