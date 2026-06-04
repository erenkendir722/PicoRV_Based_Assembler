// bram_mem.v — 64 KB BSRAM (16384 x 32-bit)
// Tang Nano 9K: text=0x0000, data=0x8000
// $readmemh ile program.mem yuklenir

module bram_mem (
    input         clk,
    input         valid,
    output reg    ready,
    input  [13:0] addr,    // 14-bit word adresi (0..16383)
    input  [31:0] wdata,
    input  [ 3:0] wstrb,
    output [31:0] rdata
);

reg [31:0] mem [0:16383];

initial $readmemh("program.mem", mem, 0, 16383);

reg [31:0] rdata_r;
assign rdata = rdata_r;

always @(posedge clk) begin
    ready   <= 0;
    rdata_r <= 0;
    if (valid) begin
        ready <= 1;
        if (wstrb[0]) mem[addr][ 7: 0] <= wdata[ 7: 0];
        if (wstrb[1]) mem[addr][15: 8] <= wdata[15: 8];
        if (wstrb[2]) mem[addr][23:16] <= wdata[23:16];
        if (wstrb[3]) mem[addr][31:24] <= wdata[31:24];
        rdata_r <= mem[addr];
    end
end

endmodule
