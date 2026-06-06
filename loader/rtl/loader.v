// loader.v — UART tabanli Loader FSM
// Protokol:
//   WRITE: AA 55 01 ADDR[31:0](BE) NWORDS(1) DATA(4*N, BE) CRC16_HI CRC16_LO
//   RUN  : AA 55 02 CRC16_HI CRC16_LO
//   ACK=0x06  NACK=0x15
//   CRC: CRC-16/CCITT-FALSE (poly=0x1021, init=0xFFFF), CMD..son veri uzerinden
module loader (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        rx_valid,
    input  wire [7:0]  rx_data,
    output reg         tx_start,
    output reg  [7:0]  tx_data,
    input  wire        tx_busy,
    output reg         mem_we,
    output reg  [13:0] mem_waddr,
    output reg  [31:0] mem_wdata,
    output reg         cpu_run
);
    localparam [7:0] SYNC0    = 8'hAA;
    localparam [7:0] SYNC1    = 8'h55;
    localparam [7:0] CMD_WRITE= 8'h01;
    localparam [7:0] CMD_RUN  = 8'h02;
    localparam [7:0] ACK      = 8'h06;
    localparam [7:0] NACK     = 8'h15;

    localparam [4:0]
        S_SYNC0  = 0, S_SYNC1  = 1, S_CMD    = 2,
        S_A3     = 3, S_A2     = 4, S_A1     = 5, S_A0    = 6,
        S_NW     = 7, S_DATA   = 8, S_CRC1   = 9, S_CRC0  = 10,
        S_REPLY  = 11,
        S_RCRC1  = 12, S_RCRC0 = 13, S_RREPLY = 14, S_RFLUSH = 15,
        S_RUNNING= 16;

    reg [4:0]  state;
    reg [31:0] addr_reg;
    reg [7:0]  nwords;
    reg [15:0] words_done;
    reg [1:0]  byte_in_word;
    reg [31:0] word_buf;
    reg [15:0] crc;
    reg [15:0] rx_crc;
    reg        reply_ack;

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

    wire [31:0] word_asm  = {word_buf[23:0], rx_data};
    wire [13:0] cur_waddr = addr_reg[15:2] + words_done[13:0];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_SYNC0; cpu_run <= 0;
            tx_start <= 0; mem_we <= 0;
            crc <= 16'hFFFF; rx_crc <= 0;
            addr_reg <= 0; nwords <= 0;
            words_done <= 0; byte_in_word <= 0;
            word_buf <= 0; reply_ack <= 0;
        end else begin
            tx_start <= 0;
            mem_we   <= 0;
            case (state)
                S_SYNC0: if (rx_valid && rx_data == SYNC0) state <= S_SYNC1;
                S_SYNC1: if (rx_valid) begin
                    if      (rx_data == SYNC1) state <= S_CMD;
                    else if (rx_data == SYNC0) state <= S_SYNC1;
                    else                       state <= S_SYNC0;
                end
                S_CMD: if (rx_valid) begin
                    crc <= crc_next(16'hFFFF, rx_data);
                    if      (rx_data == CMD_WRITE) state <= S_A3;
                    else if (rx_data == CMD_RUN)   state <= S_RCRC1;
                    else                           state <= S_SYNC0;
                end
                S_A3: if (rx_valid) begin addr_reg[31:24] <= rx_data; crc <= crc_next(crc, rx_data); state <= S_A2; end
                S_A2: if (rx_valid) begin addr_reg[23:16] <= rx_data; crc <= crc_next(crc, rx_data); state <= S_A1; end
                S_A1: if (rx_valid) begin addr_reg[15: 8] <= rx_data; crc <= crc_next(crc, rx_data); state <= S_A0; end
                S_A0: if (rx_valid) begin addr_reg[ 7: 0] <= rx_data; crc <= crc_next(crc, rx_data); state <= S_NW; end
                S_NW: if (rx_valid) begin
                    nwords       <= rx_data;
                    crc          <= crc_next(crc, rx_data);
                    words_done   <= 0;
                    byte_in_word <= 0;
                    word_buf     <= 0;
                    state        <= (rx_data == 0) ? S_CRC1 : S_DATA;
                end
                S_DATA: if (rx_valid) begin
                    crc      <= crc_next(crc, rx_data);
                    word_buf <= word_asm;
                    if (byte_in_word == 2'd3) begin
                        mem_we       <= 1;
                        mem_waddr    <= cur_waddr;
                        mem_wdata    <= word_asm;
                        byte_in_word <= 0;
                        words_done   <= words_done + 1;
                        if (words_done + 1 == {8'd0, nwords}) state <= S_CRC1;
                    end else
                        byte_in_word <= byte_in_word + 1;
                end
                S_CRC1: if (rx_valid) begin rx_crc[15:8] <= rx_data; state <= S_CRC0; end
                S_CRC0: if (rx_valid) begin
                    rx_crc[7:0] <= rx_data;
                    reply_ack   <= ({rx_crc[15:8], rx_data} == crc);
                    state       <= S_REPLY;
                end
                S_REPLY: if (!tx_busy) begin
                    tx_start <= 1;
                    tx_data  <= reply_ack ? ACK : NACK;
                    state    <= S_SYNC0;
                end
                S_RCRC1: if (rx_valid) begin rx_crc[15:8] <= rx_data; state <= S_RCRC0; end
                S_RCRC0: if (rx_valid) begin
                    rx_crc[7:0] <= rx_data;
                    reply_ack   <= ({rx_crc[15:8], rx_data} == crc);
                    state       <= S_RREPLY;
                end
                S_RREPLY: if (!tx_busy) begin
                    tx_start <= 1;
                    tx_data  <= reply_ack ? ACK : NACK;
                    state    <= reply_ack ? S_RFLUSH : S_SYNC0;
                end
                S_RFLUSH: if (!tx_busy && !tx_start) begin
                    cpu_run <= 1;
                    state   <= S_RUNNING;
                end
                // CPU calisirken yeni yukleme baslayabilir: host AA gonderince
                // CPU'yu durdurup yeniden yukleme moduna gec (S1 reset gereksiz).
                S_RUNNING:
                    if (rx_valid && rx_data == SYNC0) begin
                        cpu_run <= 0;        // CPU'yu reset'e al
                        state   <= S_SYNC1;  // 0x55 bekle, yeni paket
                    end else
                        cpu_run <= 1;
                default: state <= S_SYNC0;
            endcase
        end
    end
endmodule
