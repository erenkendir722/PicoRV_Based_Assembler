// bram_mem.v — Gowin GW1NR-9, BSRAM olarak sentezlenir
module bram_mem (
    input  wire        clk,
    input  wire        valid,
    output reg         ready,
    input  wire [ 8:0] addr,   // 9-bit = 0..511
    input  wire [31:0] wdata,
    input  wire [ 3:0] wstrb,
    output reg  [31:0] rdata
);

(* ram_style = "bram" *)
reg [31:0] mem [0:511];   // 512 word = 2KB, program 286 word

initial $readmemh("program.mem", mem, 0, 511);

always @(posedge clk) begin
    ready <= 0;
    if (valid) begin
        ready <= 1;
        if (wstrb[0]) mem[addr][ 7: 0] <= wdata[ 7: 0];
        if (wstrb[1]) mem[addr][15: 8] <= wdata[15: 8];
        if (wstrb[2]) mem[addr][23:16] <= wdata[23:16];
        if (wstrb[3]) mem[addr][31:24] <= wdata[31:24];
        rdata <= mem[addr];
    end
end

endmodule
