// ════════════════════════════════════════════════════════════════════
// bram_mem.v — Tek portlu Blok RAM (Gowin GW1NR-9 BSRAM)
// ════════════════════════════════════════════════════════════════════
// Proje 3 surumu: $readmemh ile ON-YUKLEME YOK. Bellek bos (0) baslar;
// program calisma zamaninda Loader tarafindan UART uzerinden doldurulur.
//
// Port, top_loader.v'de Loader (yukleme aninda) ile CPU (calisma aninda)
// arasinda multiplekslenir.
//
//   DEPTH = 2^AWIDTH word  (varsayilan 2048 word = 8 KB)
// ════════════════════════════════════════════════════════════════════
module bram_mem #(
    parameter AWIDTH = 11               // word adres geni
)(
    input  wire              clk,
    input  wire              valid,
    output reg               ready,
    input  wire [AWIDTH-1:0] addr,      // word adresi
    input  wire [31:0]       wdata,
    input  wire [3:0]        wstrb,
    output reg  [31:0]       rdata
);
    localparam DEPTH = (1 << AWIDTH);

    (* ram_style = "bram" *)
    reg [31:0] mem [0:DEPTH-1];

    // Sentez ve simulasyonda belirli baslangic (Gowin BSRAM 0 ile baslar)
    integer k;
    initial for (k = 0; k < DEPTH; k = k + 1) mem[k] = 32'h0;

    always @(posedge clk) begin
        ready <= 1'b0;
        if (valid) begin
            ready <= 1'b1;
            if (wstrb[0]) mem[addr][ 7: 0] <= wdata[ 7: 0];
            if (wstrb[1]) mem[addr][15: 8] <= wdata[15: 8];
            if (wstrb[2]) mem[addr][23:16] <= wdata[23:16];
            if (wstrb[3]) mem[addr][31:24] <= wdata[31:24];
            rdata <= mem[addr];
        end
    end

endmodule
