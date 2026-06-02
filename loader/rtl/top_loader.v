// ════════════════════════════════════════════════════════════════════
// top_loader.v — Tang Nano 9K: PicoRV32 + UART Loader + BRAM + GPIO
// ════════════════════════════════════════════════════════════════════
// Proje 3 ust modulu. Donanim-yazilim ortak tasarimi (co-design):
//
//   Bilgisayar (Python host)  --UART(rx)-->  [uart_rx] --> [loader FSM]
//                             <--UART(tx)--  [uart_tx] <-- ACK/NACK
//
//   Yukleme aninda  : loader BRAM'i doldurur, CPU reset'te tutulur.
//   Yukleme bitince : loader cpu_run=1 yapar, CPU PC=0x0'dan calisir.
//                     UART hatti artik CPU'ya aittir (sonuc gonderir).
//
// ── Bellek haritasi (CPU) ──────────────────────────────────────────
//   0x00000000 - 0x00001FFF : BRAM  (2048 word = 8 KB; text+data+stack)
//   0x02000000              : GPIO LED (write bit[5:0]; donanim aktif-dusuk)
//   0x03000000              : UART veri (write bit[7:0]=gonder; read bit0=busy)
//
// ── Saat / Baud ────────────────────────────────────────────────────
//   Tang Nano 9K dahili osilator 27 MHz.
//   115200 baud icin CLKS_PER_BIT = 27e6/115200 ≈ 234.
//   (Simulasyon icin testbench daha kucuk CLKS_PER_BIT verir.)
// ════════════════════════════════════════════════════════════════════
module top_loader #(
    parameter CLKS_PER_BIT = 234,
    parameter AWIDTH       = 11          // 2048 word BRAM
)(
    input  wire       clk,        // 27 MHz
    input  wire       rst_btn,    // S1 (active-low)
    input  wire       uart_rx,    // host -> fpga
    output wire       uart_tx,    // fpga -> host
    output wire [5:0] led         // LED5..LED0 (active-low)
);

    // ── Kart reset senkronizasyonu ──────────────────────────────────
    wire rst_n_raw = rst_btn;     // S1 active-low
    reg [3:0] rst_sr = 4'b0000;
    always @(posedge clk) rst_sr <= {rst_sr[2:0], rst_n_raw};
    wire rst_n = rst_sr[3];

    // ── UART alici ──────────────────────────────────────────────────
    wire       rx_valid;
    wire [7:0] rx_data;
    uart_rx #(.CLKS_PER_BIT(CLKS_PER_BIT)) U_RX (
        .clk(clk), .rst_n(rst_n),
        .i_rx(uart_rx), .o_valid(rx_valid), .o_data(rx_data)
    );

    // ── UART gonderici (loader ACK/NACK ile CPU arasinda paylasilir) ─
    wire       tx_busy;
    reg        tx_start_mux;
    reg  [7:0] tx_data_mux;
    uart_tx #(.CLKS_PER_BIT(CLKS_PER_BIT)) U_TX (
        .clk(clk), .rst_n(rst_n),
        .i_start(tx_start_mux), .i_data(tx_data_mux),
        .o_tx(uart_tx), .o_busy(tx_busy)
    );

    // ── Loader FSM ──────────────────────────────────────────────────
    wire        ld_tx_start;
    wire [7:0]  ld_tx_data;
    wire        ld_mem_we;
    wire [13:0] ld_mem_waddr;
    wire [31:0] ld_mem_wdata;
    wire        cpu_run;
    wire [15:0] loaded_words;

    loader U_LOADER (
        .clk(clk), .rst_n(rst_n),
        .rx_valid(rx_valid), .rx_data(rx_data),
        .tx_start(ld_tx_start), .tx_data(ld_tx_data), .tx_busy(tx_busy),
        .mem_we(ld_mem_we), .mem_waddr(ld_mem_waddr), .mem_wdata(ld_mem_wdata),
        .cpu_run(cpu_run),
        .loaded_words(loaded_words)
    );

    wire loading = ~cpu_run;

    // ── CPU reset: yukleme bitince serbest birak ────────────────────
    reg [2:0] cpu_run_sr = 3'b000;
    always @(posedge clk)
        cpu_run_sr <= {cpu_run_sr[1:0], (cpu_run & rst_n)};
    wire cpu_resetn = cpu_run_sr[2];

    // ── PicoRV32 ────────────────────────────────────────────────────
    wire        mem_valid;
    wire        mem_ready;
    wire [31:0] mem_addr;
    wire [31:0] mem_wdata;
    wire [ 3:0] mem_wstrb;
    wire [31:0] mem_rdata;

    picorv32 #(
        .STACKADDR      (32'h00001FF0),   // 8 KB BRAM tepesi
        .PROGADDR_RESET (32'h00000000),
        .ENABLE_MUL     (0),
        .ENABLE_DIV     (0),
        .COMPRESSED_ISA (0)
    ) cpu (
        .clk(clk), .resetn(cpu_resetn),
        .mem_valid(mem_valid), .mem_ready(mem_ready),
        .mem_addr(mem_addr), .mem_wdata(mem_wdata),
        .mem_wstrb(mem_wstrb), .mem_rdata(mem_rdata)
    );

    // ── Adres cozme (CPU) ───────────────────────────────────────────
    wire cpu_bram_sel = (mem_addr[31:AWIDTH+2] == 0);   // addr < 8 KB
    wire gpio_sel     = (mem_addr == 32'h02000000);
    wire uart_sel     = (mem_addr == 32'h03000000);

    // ── BRAM port mux: yuklemede loader, calismada CPU ──────────────
    wire              bram_valid = loading ? ld_mem_we
                                           : (mem_valid & cpu_bram_sel);
    wire [AWIDTH-1:0] bram_addr  = loading ? ld_mem_waddr[AWIDTH-1:0]
                                           : mem_addr[AWIDTH+1:2];
    wire [31:0]       bram_wdata = loading ? ld_mem_wdata : mem_wdata;
    wire [3:0]        bram_wstrb = loading ? 4'b1111
                                           : (mem_valid & cpu_bram_sel ? mem_wstrb : 4'b0);
    wire              bram_ready;
    wire [31:0]       bram_rdata;

    bram_mem #(.AWIDTH(AWIDTH)) BRAM (
        .clk(clk), .valid(bram_valid), .ready(bram_ready),
        .addr(bram_addr), .wdata(bram_wdata), .wstrb(bram_wstrb),
        .rdata(bram_rdata)
    );

    // ── GPIO LED register ───────────────────────────────────────────
    reg        gpio_ready = 0;
    reg [5:0]  led_reg = 6'b000000;
    always @(posedge clk) begin
        gpio_ready <= 0;
        if (mem_valid & gpio_sel) begin
            gpio_ready <= 1;
            if (mem_wstrb[0]) led_reg <= mem_wdata[5:0];
        end
    end
    assign led = ~led_reg;     // aktif-dusuk: yanan LED = ikilik 1

    // ── UART veri portu (CPU sonuc gonderir / busy okur) ────────────
    reg       cpu_tx_start = 0;
    reg [7:0] cpu_tx_data  = 0;
    reg       uart_ready   = 0;
    always @(posedge clk) begin
        cpu_tx_start <= 0;
        uart_ready   <= 0;
        if (mem_valid & uart_sel) begin
            uart_ready <= 1;
            if (mem_wstrb[0] & ~tx_busy) begin
                cpu_tx_start <= 1;
                cpu_tx_data  <= mem_wdata[7:0];
            end
        end
    end

    // ── UART TX kaynagi: yuklemede loader, calismada CPU ────────────
    always @(*) begin
        if (loading) begin
            tx_start_mux = ld_tx_start;
            tx_data_mux  = ld_tx_data;
        end else begin
            tx_start_mux = cpu_tx_start;
            tx_data_mux  = cpu_tx_data;
        end
    end

    // ── Bus geri donus mux (CPU) ────────────────────────────────────
    assign mem_ready = cpu_bram_sel ? bram_ready :
                       gpio_sel     ? gpio_ready :
                       uart_sel     ? uart_ready : 1'b0;
    assign mem_rdata = cpu_bram_sel ? bram_rdata :
                       uart_sel     ? {31'b0, tx_busy} : 32'h0;

endmodule
