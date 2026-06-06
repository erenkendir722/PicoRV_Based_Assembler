// bram_mem.v — Tek portlu senkron BRAM (1 KB = 256 x 32-bit)
// ─────────────────────────────────────────────────────────────────────
// Gowin BSRAM (SP) icin ders-kitabi cikarim deseni: TEK yazma/okuma portu,
// byte-enable yazma, senkron okuma. Loader ve CPU asla ayni anda erismez
// (loader cpu_run=0 iken yazar, CPU cpu_run=1 iken erisir); bu yuzden iki
// erisim top_loader icinde tek porta mux'lanir ve burada tek port yeter.
module bram_mem (
    input  wire        clk,
    input  wire [ 3:0] we,      // byte yazma izinleri
    input  wire [ 7:0] addr,    // word adresi 0..255
    input  wire [31:0] din,
    output reg  [31:0] dout
);
    reg [31:0] mem [0:255];

    always @(posedge clk) begin
        if (we[0]) mem[addr][ 7: 0] <= din[ 7: 0];
        if (we[1]) mem[addr][15: 8] <= din[15: 8];
        if (we[2]) mem[addr][23:16] <= din[23:16];
        if (we[3]) mem[addr][31:24] <= din[31:24];
        dout <= mem[addr];
    end
endmodule
