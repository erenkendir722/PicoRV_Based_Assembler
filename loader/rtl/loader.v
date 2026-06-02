// ════════════════════════════════════════════════════════════════════
// loader.v — UART tabanli Program Yukleyici (Loader) Sonlu Durum Makinesi
// ════════════════════════════════════════════════════════════════════
// Proje 3'un cekirdegi. Bilgisayardan UART ile gelen paketleri yakalar,
// CRC-16 ile butunlugunu dogrular, makine kodunu blok bellege (BRAM)
// dogru adreslere yazar; yukleme bitince CPU'yu reset'ten birakir.
//
// Yukleme suresince cpu_run = 0  -> CPU reset/bekleme modunda tutulur.
// RUN paketi dogrulanunca cpu_run = 1 -> CPU PC=0x0'dan calismaya baslar.
//
// ── Paket protokolu (host -> fpga) ─────────────────────────────────
//   WRITE: AA 55 01 ADDR[31:0](BE,4 bayt) NWORDS(1) DATA(4*N, BE word)
//          CRC16_HI CRC16_LO
//          CRC, [CMD .. son veri bayti] uzerinden hesaplanir.
//   RUN  : AA 55 02 CRC16_HI CRC16_LO     (CRC, sadece CMD uzerinden)
//
// ── Cevap (fpga -> host) ───────────────────────────────────────────
//   ACK  = 0x06  (CRC dogru)
//   NACK = 0x15  (CRC hatali -> host paketi tekrar gonderir)
//
// CRC = CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF). Host (crc16.py)
// ile birebir ayni; bkz. rapor bolum 1.2 (Seri Haberlesme/Veri Dogrulama).
// ════════════════════════════════════════════════════════════════════
module loader (
    input  wire        clk,
    input  wire        rst_n,

    // ── UART alici arayuzu ──────────────────────────────────────────
    input  wire        rx_valid,    // 1 darbe: yeni bayt geldi
    input  wire [7:0]  rx_data,

    // ── UART gonderici arayuzu (ACK/NACK) ───────────────────────────
    output reg         tx_start,
    output reg  [7:0]  tx_data,
    input  wire        tx_busy,

    // ── BRAM yazma arayuzu (yukleme sirasinda) ──────────────────────
    output reg         mem_we,      // 1 darbe: word yaz
    output reg [13:0]  mem_waddr,   // word adresi (32-bit hizali word index)
    output reg [31:0]  mem_wdata,

    // ── CPU kontrolu ────────────────────────────────────────────────
    output reg         cpu_run,     // 0: reset'te tut, 1: calistir

    // ── Hata ayiklama / metrik ──────────────────────────────────────
    output reg [15:0]  loaded_words // yuklenen toplam word sayisi
);

    // ── Komut kodlari ───────────────────────────────────────────────
    localparam [7:0] CMD_WRITE = 8'h01;
    localparam [7:0] CMD_RUN   = 8'h02;
    localparam [7:0] SYNC0     = 8'hAA;
    localparam [7:0] SYNC1     = 8'h55;
    localparam [7:0] ACK       = 8'h06;
    localparam [7:0] NACK      = 8'h15;

    // ── Durumlar ─────────────────────────────────────────────────────
    localparam [4:0]
        S_SYNC0    = 5'd0,
        S_SYNC1    = 5'd1,
        S_CMD      = 5'd2,
        S_A3       = 5'd3,
        S_A2       = 5'd4,
        S_A1       = 5'd5,
        S_A0       = 5'd6,
        S_NW       = 5'd7,
        S_DATA     = 5'd8,
        S_CRC1     = 5'd9,
        S_CRC0     = 5'd10,
        S_REPLY    = 5'd11,
        S_RCRC1    = 5'd12,
        S_RCRC0    = 5'd13,
        S_RREPLY   = 5'd14,
        S_RFLUSH   = 5'd15,
        S_RUNNING  = 5'd16;

    reg [4:0]  state;
    reg [31:0] addr_reg;       // paketin baz bayt adresi
    reg [7:0]  nwords;         // paketteki word sayisi
    reg [15:0] words_done;     // bu pakette yazilan word sayisi
    reg [1:0]  byte_in_word;   // 0..3
    reg [31:0] word_buf;       // toplanan word (big-endian)
    reg [15:0] crc;            // calisan CRC
    reg [15:0] rx_crc;         // host'tan gelen CRC
    reg        reply_ack;      // S_REPLY: ACK mi NACK mi gonderilecek

    // ── CRC-16/CCITT-FALSE bayt guncelleme (kombinasyonel) ───────────
    function [15:0] crc_next;
        input [15:0] c_in;
        input [7:0]  d;
        reg   [15:0] c;
        integer i;
        begin
            c = c_in ^ {d, 8'h00};
            for (i = 0; i < 8; i = i + 1)
                c = c[15] ? ((c << 1) ^ 16'h1021) : (c << 1);
            crc_next = c;
        end
    endfunction

    // word_buf'a yeni bayt eklenince olusan tam word (big-endian)
    wire [31:0] word_asm = {word_buf[23:0], rx_data};
    // mevcut yazilacak word adresi: baz word + bu pakette yazilanlar
    wire [13:0] cur_waddr = addr_reg[15:2] + words_done[13:0];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state        <= S_SYNC0;
            cpu_run      <= 1'b0;       // CPU reset'te
            tx_start     <= 1'b0;
            tx_data      <= 8'h00;
            mem_we       <= 1'b0;
            mem_waddr    <= 14'd0;
            mem_wdata    <= 32'd0;
            addr_reg     <= 32'd0;
            nwords       <= 8'd0;
            words_done   <= 16'd0;
            byte_in_word <= 2'd0;
            word_buf     <= 32'd0;
            crc          <= 16'hFFFF;
            rx_crc       <= 16'd0;
            reply_ack    <= 1'b0;
            loaded_words <= 16'd0;
        end else begin
            // varsayilan: tek-darbe sinyalleri sifirla
            tx_start <= 1'b0;
            mem_we   <= 1'b0;

            case (state)
                // ── Senkron baytlari (AA 55) ─────────────────────────
                S_SYNC0: begin
                    if (rx_valid && rx_data == SYNC0)
                        state <= S_SYNC1;
                end

                S_SYNC1: begin
                    if (rx_valid) begin
                        if (rx_data == SYNC1)       state <= S_CMD;
                        else if (rx_data == SYNC0)  state <= S_SYNC1;
                        else                        state <= S_SYNC0;
                    end
                end

                // ── Komut bayti ──────────────────────────────────────
                S_CMD: begin
                    if (rx_valid) begin
                        crc <= crc_next(16'hFFFF, rx_data);  // CRC CMD'den baslar
                        if (rx_data == CMD_WRITE)      state <= S_A3;
                        else if (rx_data == CMD_RUN)   state <= S_RCRC1;
                        else                           state <= S_SYNC0;
                    end
                end

                // ── 4 baytlik adres (big-endian) ─────────────────────
                S_A3: if (rx_valid) begin addr_reg[31:24] <= rx_data; crc <= crc_next(crc, rx_data); state <= S_A2; end
                S_A2: if (rx_valid) begin addr_reg[23:16] <= rx_data; crc <= crc_next(crc, rx_data); state <= S_A1; end
                S_A1: if (rx_valid) begin addr_reg[15: 8] <= rx_data; crc <= crc_next(crc, rx_data); state <= S_A0; end
                S_A0: if (rx_valid) begin addr_reg[ 7: 0] <= rx_data; crc <= crc_next(crc, rx_data); state <= S_NW; end

                // ── Word sayisi ──────────────────────────────────────
                S_NW: if (rx_valid) begin
                    nwords       <= rx_data;
                    crc          <= crc_next(crc, rx_data);
                    words_done   <= 16'd0;
                    byte_in_word <= 2'd0;
                    word_buf     <= 32'd0;
                    state        <= (rx_data == 8'd0) ? S_CRC1 : S_DATA;
                end

                // ── Veri baytlari -> word topla, BRAM'e yaz ──────────
                S_DATA: if (rx_valid) begin
                    crc      <= crc_next(crc, rx_data);
                    word_buf <= word_asm;
                    if (byte_in_word == 2'd3) begin
                        // 4 bayt tamamlandi -> tam word'u BRAM'e yaz
                        mem_we     <= 1'b1;
                        mem_waddr  <= cur_waddr;
                        mem_wdata  <= word_asm;
                        byte_in_word <= 2'd0;
                        words_done <= words_done + 1'b1;
                        if (words_done + 1'b1 == {8'd0, nwords})
                            state <= S_CRC1;
                    end else begin
                        byte_in_word <= byte_in_word + 1'b1;
                    end
                end

                // ── Gelen CRC (2 bayt, big-endian) ───────────────────
                S_CRC1: if (rx_valid) begin rx_crc[15:8] <= rx_data; state <= S_CRC0; end
                S_CRC0: if (rx_valid) begin
                    rx_crc[7:0] <= rx_data;
                    reply_ack   <= ({rx_crc[15:8], rx_data} == crc);
                    state       <= S_REPLY;
                    if ({rx_crc[15:8], rx_data} == crc)
                        loaded_words <= loaded_words + words_done;
                end

                // ── WRITE cevabi: ACK/NACK gonder ────────────────────
                S_REPLY: if (!tx_busy) begin
                    tx_start <= 1'b1;
                    tx_data  <= reply_ack ? ACK : NACK;
                    state    <= S_SYNC0;     // sonraki paketi bekle
                end

                // ── RUN paketi CRC ───────────────────────────────────
                S_RCRC1: if (rx_valid) begin rx_crc[15:8] <= rx_data; state <= S_RCRC0; end
                S_RCRC0: if (rx_valid) begin
                    rx_crc[7:0] <= rx_data;
                    reply_ack   <= ({rx_crc[15:8], rx_data} == crc);
                    state       <= S_RREPLY;
                end

                // ── RUN cevabi: ACK gonder (CRC OK ise) ──────────────
                S_RREPLY: if (!tx_busy) begin
                    tx_start <= 1'b1;
                    tx_data  <= reply_ack ? ACK : NACK;
                    state    <= reply_ack ? S_RFLUSH : S_SYNC0;
                end

                // ── ACK tam gonderilene kadar bekle, sonra CPU'yu birak
                S_RFLUSH: begin
                    if (tx_busy == 1'b0 && tx_start == 1'b0) begin
                        // ACK gonderimi bitti -> reset hattini serbest birak
                        cpu_run <= 1'b1;
                        state   <= S_RUNNING;
                    end
                end

                // ── CPU calisiyor; loader bekler ─────────────────────
                S_RUNNING: begin
                    cpu_run <= 1'b1;
                end

                default: state <= S_SYNC0;
            endcase
        end
    end

endmodule
