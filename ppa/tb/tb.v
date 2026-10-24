`timescale 1ns/1ps
// Self-checking testbench: runs sw/bench.hex, hashes every memory write,
// and stops when the program writes its result to 0x10000000.
// RTL sim:   iverilog -g2012 -DBS=<0|1> tb/tb.v rtl/<variant>/picorv32.v
// Gate sim:  iverilog -g2012 -DGATE tb/tb.v build/<run>/netlist.v   (optionally -DVCD='"x.vcd"')
module tb;
  reg clk = 0, resetn = 0;
  always #5 clk = ~clk;
  wire trap, mem_valid, mem_instr;
  reg  mem_ready = 0;
  wire [31:0] mem_addr, mem_wdata;
  wire [3:0]  mem_wstrb;
  reg  [31:0] mem_rdata;
  reg  [31:0] mem [0:16383];
  reg  [31:0] hash;
  integer cycles = 0, i;

`ifdef GATE
  picorv32 uut (
`else
  picorv32 #(.BARREL_SHIFTER(`BS)) uut (
`endif
    .clk(clk), .resetn(resetn), .trap(trap),
    .mem_valid(mem_valid), .mem_instr(mem_instr), .mem_ready(mem_ready),
    .mem_addr(mem_addr), .mem_wdata(mem_wdata), .mem_wstrb(mem_wstrb), .mem_rdata(mem_rdata),
    .pcpi_wr(1'b0), .pcpi_rd(32'b0), .pcpi_wait(1'b0), .pcpi_ready(1'b0), .irq(32'b0));

  initial begin
    for (i = 0; i < 16384; i = i + 1) mem[i] = 0;
    $readmemh("sw/bench.hex", mem);
    hash = 32'h811c9dc5;
`ifdef VCD
    $dumpfile(`VCD);
`endif
    repeat (5) @(posedge clk);
    resetn <= 1;
`ifdef VCD
    $dumpvars(1, uut);
`endif
  end

  always @(posedge clk) begin
    cycles <= cycles + 1;
    mem_ready <= mem_valid && !mem_ready;
    mem_rdata <= mem[mem_addr[15:2]];
    if (mem_valid && !mem_ready && mem_wstrb) begin
      if (mem_addr == 32'h10000000) begin
        $display("RESULT=%08x HASH=%08x CYCLES=%0d", mem_wdata, hash, cycles);
        $finish;
      end
      if (mem_wstrb[0]) mem[mem_addr[15:2]][ 7: 0] <= mem_wdata[ 7: 0];
      if (mem_wstrb[1]) mem[mem_addr[15:2]][15: 8] <= mem_wdata[15: 8];
      if (mem_wstrb[2]) mem[mem_addr[15:2]][23:16] <= mem_wdata[23:16];
      if (mem_wstrb[3]) mem[mem_addr[15:2]][31:24] <= mem_wdata[31:24];
      hash <= {hash[26:0], hash[31:27]} ^ mem_wdata ^ {mem_addr[15:0], 12'h0, mem_wstrb};
    end
    if (resetn && trap) begin $display("TRAP"); $finish; end
    if (cycles > 400000) begin $display("TIMEOUT"); $finish; end
  end
endmodule
