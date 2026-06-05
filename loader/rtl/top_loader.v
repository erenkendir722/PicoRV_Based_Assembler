// top_loader.v — Tang Nano 9K: UART Loader + PicoRV32
// Saat: 27 MHz  Baud: 115200  BRAM: 8 KB
// Bellek haritasi (CPU):
//   0x00000000-0x00001FFF  BRAM (8 KB)
//   0x02000000             GPIO LED (bit[5:0], aktif-dusuk)
//   0x03000000             UART TX (yaz=gonder, oku bit0=busy)
module top_loader (
    input  wire       clk,
    input  wire       rst_btn,
    input  wire       uart_rx,
    output wire       uart_tx,
    output wire [5:0] led
);
    // ── Reset ────────────────────────────────────────────────────────
    reg [3:0] rst_sr = 4'b0000;
    always @(posedge clk) rst_sr <= {rst_sr[2:0], rst_btn};
    wire rst_n = rst_sr[3];

    // ── UART RX ──────────────────────────────────────────────────────
    wire       rx_valid;
    wire [7:0] rx_data;
    uart_rx #(.CLKS_PER_BIT(234)) urx (
        .clk(clk), .rst_n(rst_n),
        .rx(uart_rx), .valid(rx_valid), .data(rx_data)
    );

    // ── Loader FSM ───────────────────────────────────────────────────
    wire        cpu_run;
    wire        ldr_tx_start;
    wire [7:0]  ldr_tx_data;
    wire        mem_we;
    wire [13:0] mem_waddr;
    wire [31:0] mem_wdata_ldr;
    wire        tx_busy;

    loader ldr (
        .clk(clk), .rst_n(rst_n),
        .rx_valid(rx_valid), .rx_data(rx_data),
        .tx_start(ldr_tx_start), .tx_data(ldr_tx_data), .tx_busy(tx_busy),
        .mem_we(mem_we), .mem_waddr(mem_waddr), .mem_wdata(mem_wdata_ldr),
        .cpu_run(cpu_run)
    );

    // ── PicoRV32 ─────────────────────────────────────────────────────
    wire        cpu_valid;
    wire [31:0] mem_addr;
    wire [31:0] mem_wdata_cpu;
    wire [ 3:0] mem_wstrb;
    wire [31:0] mem_rdata;
    wire        mem_ready;

    picorv32 #(
        .STACKADDR    (32'h00001FF0),
        .PROGADDR_RESET(32'h00000000),
        .ENABLE_MUL   (0),
        .ENABLE_DIV   (0),
        .COMPRESSED_ISA(0)
    ) cpu (
        .clk      (clk),
        .resetn   (cpu_run),
        .mem_valid(cpu_valid),
        .mem_ready(mem_ready),
        .mem_addr (mem_addr),
        .mem_wdata(mem_wdata_cpu),
        .mem_wstrb(mem_wstrb),
        .mem_rdata(mem_rdata)
    );

    // ── BRAM ─────────────────────────────────────────────────────────
    wire bram_sel   = (mem_addr[31:13] == 19'd0);
    wire bram_ready;
    wire [31:0] bram_rdata;

    bram_mem bram (
        .clk(clk),
        .a_we(mem_we), .a_addr(mem_waddr[10:0]), .a_wdata(mem_wdata_ldr),
        .b_valid(cpu_valid & bram_sel),
        .b_ready(bram_ready),
        .b_addr(mem_addr[12:2]),
        .b_wdata(mem_wdata_cpu),
        .b_wstrb(mem_wstrb),
        .b_rdata(bram_rdata)
    );

    // ── GPIO @ 0x02000000 ────────────────────────────────────────────
    wire gpio_sel = (mem_addr == 32'h02000000);
    reg  gpio_rdy = 0;
    reg [5:0] led_reg = 6'b111111;

    always @(posedge clk) begin
        gpio_rdy <= 0;
        if (cpu_valid & gpio_sel) begin
            gpio_rdy <= 1;
            if (mem_wstrb[0]) led_reg <= mem_wdata_cpu[5:0];
        end
    end
    assign led = ~led_reg;

    // ── UART TX CPU tarafı @ 0x03000000 ─────────────────────────────
    wire uart_sel = (mem_addr == 32'h03000000);
    reg  uart_rdy       = 0;
    reg  cpu_tx_start_r = 0;
    reg  [7:0] cpu_tx_data_r = 0;

    always @(posedge clk) begin
        uart_rdy       <= 0;
        cpu_tx_start_r <= 0;
        if (cpu_valid & uart_sel) begin
            uart_rdy <= 1;
            if (mem_wstrb[0] && !tx_busy) begin
                cpu_tx_data_r  <= mem_wdata_cpu[7:0];
                cpu_tx_start_r <= 1;
            end
        end
    end

    // ── UART TX mux: yükleme=loader, çalışma=CPU ─────────────────────
    uart_tx #(.CLKS_PER_BIT(234)) utx (
        .clk(clk), .rst_n(rst_n),
        .start(cpu_run ? cpu_tx_start_r : ldr_tx_start),
        .data (cpu_run ? cpu_tx_data_r  : ldr_tx_data),
        .busy(tx_busy), .tx(uart_tx)
    );

    // ── Bus mux ──────────────────────────────────────────────────────
    assign mem_ready = bram_sel ? bram_ready :
                       gpio_sel ? gpio_rdy   :
                       uart_sel ? uart_rdy   : 1'b1;
    assign mem_rdata = bram_sel ? bram_rdata         :
                       uart_sel ? {31'd0, tx_busy}   : 32'h0;

endmodule
