// top.v — Tang Nano 9K: PicoRV32 + BRAM + GPIO
// Mors kodu LED sürücüsü
// Saat: 27 MHz (Tang Nano 9K dahili osc)
// LED0 (pin 10): mors çıkışı  GPIO @ 0x02000000 bit0

module top (
    input  wire clk,        // 27 MHz
    input  wire rst_btn,    // S1 butonu (active-low)
    output wire led_morse   // LED0
);

// ── Reset ──────────────────────────────────────────────────────────────
wire rst_n = rst_btn;  // Tang Nano S1 active-low
reg [3:0] reset_sr = 4'b0000;
always @(posedge clk)
    reset_sr <= {reset_sr[2:0], rst_n};
wire cpu_resetn = reset_sr[3];

// ── PicoRV32 ───────────────────────────────────────────────────────────
wire        mem_valid;
wire        mem_ready;
wire [31:0] mem_addr;
wire [31:0] mem_wdata;
wire [ 3:0] mem_wstrb;
wire [31:0] mem_rdata;

picorv32 #(
    .STACKADDR (32'h000007F0),
    .PROGADDR_RESET (32'h00000000),
    .ENABLE_MUL (0),
    .ENABLE_DIV (0),
    .COMPRESSED_ISA (0)
) cpu (
    .clk       (clk),
    .resetn    (cpu_resetn),
    .mem_valid (mem_valid),
    .mem_ready (mem_ready),
    .mem_addr  (mem_addr),
    .mem_wdata (mem_wdata),
    .mem_wstrb (mem_wstrb),
    .mem_rdata (mem_rdata)
);

// ── BRAM (64KB) ────────────────────────────────────────────────────────
// 0x00000000 - 0x0000FFFF  (text + data + stack)
// bram_sel: üst 16 bit sıfır (adres < 0x10000)
wire bram_sel   = (mem_addr[31:11] == 21'h0);  // adres < 0x800
wire bram_ready;
wire [31:0] bram_rdata;

bram_mem bram (
    .clk    (clk),
    .valid  (mem_valid & bram_sel),
    .ready  (bram_ready),
    .addr   (mem_addr[10:2]),   // 9-bit word addr: 0..511
    .wdata  (mem_wdata),
    .wstrb  (mem_wstrb),
    .rdata  (bram_rdata)
);

// ── GPIO (0x02000000) ──────────────────────────────────────────────────
wire gpio_sel   = (mem_addr == 32'h02000000);
reg  gpio_ready = 0;
reg  led_reg    = 0;

always @(posedge clk) begin
    gpio_ready <= 0;
    if (mem_valid & gpio_sel) begin
        gpio_ready <= 1;
        if (mem_wstrb[0])
            led_reg <= mem_wdata[0];
    end
end

assign led_morse = led_reg;

// ── Bus mux ───────────────────────────────────────────────────────────
assign mem_ready = bram_sel  ? bram_ready :
                   gpio_sel  ? gpio_ready : 1'b0;
assign mem_rdata = bram_sel  ? bram_rdata : 32'h0;

endmodule
