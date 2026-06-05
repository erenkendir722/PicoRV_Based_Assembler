// uart_tx.v — 8N1 UART gonderici
module uart_tx #(
    parameter CLKS_PER_BIT = 234
)(
    input  wire       clk,
    input  wire       rst_n,
    input  wire       start,   // 1 darbe: gonder
    input  wire [7:0] data,
    output reg        busy,
    output reg        tx
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
            state <= S_IDLE; tx <= 1; busy <= 0;
        end else begin
            case (state)
                S_IDLE: begin
                    tx   <= 1;
                    busy <= 0;
                    if (start) begin
                        shift <= data;
                        cnt   <= CLKS_PER_BIT - 1;
                        busy  <= 1;
                        tx    <= 0;
                        state <= S_START;
                    end
                end
                S_START:
                    if (cnt == 0) begin
                        tx    <= shift[0];
                        shift <= {1'b1, shift[7:1]};
                        cnt   <= CLKS_PER_BIT - 1;
                        bit_i <= 0;
                        state <= S_DATA;
                    end else
                        cnt <= cnt - 1;
                S_DATA:
                    if (cnt == 0) begin
                        if (bit_i == 7) begin
                            tx    <= 1;
                            cnt   <= CLKS_PER_BIT - 1;
                            state <= S_STOP;
                        end else begin
                            bit_i <= bit_i + 1;
                            tx    <= shift[0];
                            shift <= {1'b1, shift[7:1]};
                            cnt   <= CLKS_PER_BIT - 1;
                        end
                    end else
                        cnt <= cnt - 1;
                S_STOP:
                    if (cnt == 0) begin
                        tx    <= 1;
                        busy  <= 0;
                        state <= S_IDLE;
                    end else
                        cnt <= cnt - 1;
            endcase
        end
    end
endmodule
