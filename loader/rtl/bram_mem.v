// bram_mem.v — Çift portlu BRAM (8 KB = 2048 x 32-bit)
// Port A: loader yazmasi  Port B: CPU okuma/yazmasi
module bram_mem (
    input  wire        clk,
    // Port A — loader yazar
    input  wire        a_we,
    input  wire [10:0] a_addr,   // word adresi 0..2047
    input  wire [31:0] a_wdata,
    // Port B — CPU erisir
    input  wire        b_valid,
    output reg         b_ready,
    input  wire [10:0] b_addr,
    input  wire [31:0] b_wdata,
    input  wire [ 3:0] b_wstrb,
    output reg  [31:0] b_rdata
);
    reg [31:0] mem [0:2047];

    // Port A: loader yazma (öncelikli, sync)
    always @(posedge clk)
        if (a_we) mem[a_addr] <= a_wdata;

    // Port B: CPU okuma/yazma
    always @(posedge clk) begin
        b_ready <= 0;
        if (b_valid) begin
            b_ready <= 1;
            if (b_wstrb[0]) mem[b_addr][ 7: 0] <= b_wdata[ 7: 0];
            if (b_wstrb[1]) mem[b_addr][15: 8] <= b_wdata[15: 8];
            if (b_wstrb[2]) mem[b_addr][23:16] <= b_wdata[23:16];
            if (b_wstrb[3]) mem[b_addr][31:24] <= b_wdata[31:24];
            b_rdata <= mem[b_addr];
        end
    end
endmodule
