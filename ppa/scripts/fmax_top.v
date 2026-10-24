// Timing wrapper used ONLY for the iCE40 Fmax measurement.
// PicoRV32 has far more I/O than an iCE40 package offers, so the wrapper feeds the core
// from a serial shift register and registers every core output into one wide register
// that is selected bit-by-bit onto a single pin. No logic is added on the core's own paths.
module fmax_top (input clk, input din, output reg dout);
  reg [33:0] in_sr;
  always @(posedge clk) in_sr <= {in_sr[32:0], din};

  wire trap, mem_valid, mem_instr, mem_la_read, mem_la_write, pcpi_valid, trace_valid;
  wire [31:0] mem_addr, mem_wdata, mem_la_addr, mem_la_wdata, pcpi_insn, pcpi_rs1, pcpi_rs2, eoi;
  wire [3:0]  mem_wstrb, mem_la_wstrb;
  wire [35:0] trace_data;

  picorv32 core (
    .clk(clk), .resetn(in_sr[33]), .trap(trap),
    .mem_valid(mem_valid), .mem_instr(mem_instr), .mem_ready(in_sr[32]),
    .mem_addr(mem_addr), .mem_wdata(mem_wdata), .mem_wstrb(mem_wstrb), .mem_rdata(in_sr[31:0]),
    .mem_la_read(mem_la_read), .mem_la_write(mem_la_write), .mem_la_addr(mem_la_addr),
    .mem_la_wdata(mem_la_wdata), .mem_la_wstrb(mem_la_wstrb),
    .pcpi_valid(pcpi_valid), .pcpi_insn(pcpi_insn), .pcpi_rs1(pcpi_rs1), .pcpi_rs2(pcpi_rs2),
    .pcpi_wr(1'b0), .pcpi_rd(32'b0), .pcpi_wait(1'b0), .pcpi_ready(1'b0),
    .irq(32'b0), .eoi(eoi), .trace_valid(trace_valid), .trace_data(trace_data));

  reg [255:0] out_q;
  reg [7:0] idx;
  always @(posedge clk) begin
    out_q <= {trap, mem_valid, mem_instr, mem_la_read, mem_la_write, pcpi_valid,
              mem_addr, mem_wdata, mem_wstrb, mem_la_addr, mem_la_wdata, mem_la_wstrb,
              pcpi_insn, pcpi_rs1[15:0], pcpi_rs2[15:0], eoi[15:0]};
    idx  <= idx + 1;
    dout <= out_q[idx];
  end
endmodule
