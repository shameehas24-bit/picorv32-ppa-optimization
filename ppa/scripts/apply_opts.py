#!/usr/bin/env python3
"""Generate an optimized picorv32.v from the original by applying selected RTL edits.

usage: apply_opts.py <in.v> <out.v> E1,E2,...
  E1  shared comparator (one subtractor gives signed + unsigned less-than)
  E2  shared bidirectional shifter (bit-reverse trick; barrel-shifter config)
  E3  carry-gated 64-bit counters (upper half only changes on lower-half wrap)
  E4  hold ALU result registers once latched (no re-capture toggling)
"""
import sys

src, dst, sel = sys.argv[1], sys.argv[2], set(sys.argv[3].split(",")) - {""}
s = open(src).read()

def rep(old, new):
    global s
    assert s.count(old) == 1, ("pattern not unique/found", old)
    s = s.replace(old, new)

if "E1" in sel:
    rep("\t\t\talu_lts <= $signed(reg_op1) < $signed(reg_op2);\n\t\t\talu_ltu <= reg_op1 < reg_op2;\n",
        "\t\t\talu_lts <= alu_lts_w;\n\t\t\talu_ltu <= alu_ltu_w;\n")
    rep("\t\t\talu_lts = $signed(reg_op1) < $signed(reg_op2);\n\t\t\talu_ltu = reg_op1 < reg_op2;\n",
        "\t\t\talu_lts = alu_lts_w;\n\t\t\talu_ltu = alu_ltu_w;\n")
if "E2" in sel:
    rep("\t\t\talu_shl <= reg_op1 << reg_op2[4:0];\n\t\t\talu_shr <= $signed({instr_sra || instr_srai ? reg_op1[31] : 1'b0, reg_op1}) >>> reg_op2[4:0];\n",
        "\t\t\talu_shl <= rev32(alu_shift_res);\n\t\t\talu_shr <= alu_shift_res;\n")
    rep("\t\t\talu_shl = reg_op1 << reg_op2[4:0];\n\t\t\talu_shr = $signed({instr_sra || instr_srai ? reg_op1[31] : 1'b0, reg_op1}) >>> reg_op2[4:0];\n",
        "\t\t\talu_shl = rev32(alu_shift_res);\n\t\t\talu_shr = alu_shift_res;\n")

decl = ""
if "E1" in sel:
    decl += """\t// PPA (E1): one shared subtractor yields both the signed and unsigned less-than results
\t// (the original used two separate comparators).
\twire [32:0] alu_cmp_diff = {1'b0, reg_op1} - {1'b0, reg_op2};
\twire alu_ltu_w = alu_cmp_diff[32];
\twire alu_lts_w = (reg_op1[31] == reg_op2[31]) ? alu_cmp_diff[32] : reg_op1[31];

"""
if "E2" in sel:
    decl += """\t// PPA (E2): one shared right shifter serves both directions. A left shift is performed as
\t// bit-reverse -> logical right shift -> bit-reverse (reversal is only wiring).
\tfunction [31:0] rev32(input [31:0] x);
\t\tinteger k;
\t\tfor (k = 0; k < 32; k = k + 1) rev32[k] = x[31-k];
\tendfunction
\twire alu_shift_left = instr_sll || instr_slli;
\twire [31:0] alu_shift_in = alu_shift_left ? rev32(reg_op1) : reg_op1;
\twire [31:0] alu_shift_res = $signed({instr_sra || instr_srai ? reg_op1[31] : 1'b0, alu_shift_in}) >>> reg_op2[4:0];

"""
if decl:
    rep("\tgenerate if (TWO_CYCLE_ALU) begin\n\t\talways @(posedge clk) begin\n\t\t\talu_add_sub",
        decl + "\tgenerate if (TWO_CYCLE_ALU) begin\n\t\talways @(posedge clk) begin\n\t\t\talu_add_sub")

if "E3" in sel:
    rep("\t\t\tcount_cycle <= resetn ? count_cycle + 1 : 0;\n",
"""\t\t\t// PPA (E3): upper 32 bits only toggle when the lower half wraps
\t\t\tcount_cycle[31:0] <= resetn ? count_cycle[31:0] + 1 : 0;
\t\t\tif (!resetn)
\t\t\t\tcount_cycle[63:32] <= 0;
\t\t\telse if (&count_cycle[31:0])
\t\t\t\tcount_cycle[63:32] <= count_cycle[63:32] + 1;
""")
    rep("\t\t\t\t\t\tcount_instr <= count_instr + 1;\n",
"""\t\t\t\t\t\tcount_instr[31:0] <= count_instr[31:0] + 1;
\t\t\t\t\t\tif (&count_instr[31:0])
\t\t\t\t\t\t\tcount_instr[63:32] <= count_instr[63:32] + 1;
""")
if "E4" in sel:
    rep("\t\talu_out_0_q <= alu_out_0;\n\t\talu_out_q <= alu_out;\n",
"""\t\t// PPA (E4): freeze the ALU result registers once the result is latched
\t\tif (!latched_stalu) begin
\t\t\talu_out_0_q <= alu_out_0;
\t\t\talu_out_q <= alu_out;
\t\tend
""")
open(dst, "w").write(s)
