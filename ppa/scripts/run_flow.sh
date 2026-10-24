#!/bin/bash
# PPA flow for one design variant and one parameter configuration.
# usage: scripts/run_flow.sh <orig|opt> <config-name> <BARREL_SHIFTER 0|1>
# Outputs a one-line summary to results/<variant>-<config>.txt
set -e
cd "$(dirname "$0")/.."
V=$1; CFG=$2; BS=$3
OUT=build/$V-$CFG
mkdir -p "$OUT" results
CH="chparam -set BARREL_SHIFTER $BS picorv32;"

# ---------- 1. Technology-independent gate-level synthesis (area + logic depth) ----------
yosys -q -l "$OUT/asic.log" -p "
  read_verilog rtl/$V/picorv32.v; $CH hierarchy -top picorv32;
  synth -flatten -top picorv32;
  abc -g AND,NAND,OR,NOR,XOR,XNOR,MUX;
  opt_clean;
  tee -o $OUT/asic_stat.txt stat;
  tee -o $OUT/ltp.txt ltp -noff;
  write_verilog -noattr $OUT/netlist.v" >/dev/null
CELLS=$(grep -E "^ +Number of cells:" "$OUT/asic_stat.txt" | awk '{print $4}')
FFS=$(grep -E "DFF" "$OUT/asic_stat.txt" | awk '{s+=$2} END{print s}')
COMB=$((CELLS-FFS))
DEPTH=$(grep -o "length=[0-9]*" "$OUT/ltp.txt" | head -1 | cut -d= -f2)

# ---------- 2. iCE40 HX8K: LUTs and post-place-and-route Fmax ----------
# LUTs come from the bare core; Fmax comes from the core inside scripts/fmax_top.v
# (an I/O-reducing wrapper) so nextpnr's pin limit does not block placement.
yosys -q -l "$OUT/ice.log" -p "
  read_verilog rtl/$V/picorv32.v; $CH hierarchy -top picorv32;
  synth_ice40 -top picorv32 -json $OUT/ice.json;
  tee -o $OUT/ice_stat.txt stat" >/dev/null
LUTS=$(grep -E "SB_LUT4" "$OUT/ice_stat.txt" | awk '{print $2}')
yosys -q -l "$OUT/ice_top.log" -p "
  read_verilog rtl/$V/picorv32.v scripts/fmax_top.v; $CH hierarchy -top fmax_top;
  synth_ice40 -top fmax_top -json $OUT/ice_top.json" >/dev/null
FMAXS=""
for SEED in 1 2 3 4 5; do
  nextpnr-ice40 --hx8k --package ct256 --json "$OUT/ice_top.json" --freq 100 --seed $SEED \
    --pcf-allow-unconstrained --placer heap -l "$OUT/pnr_$SEED.log" -q >/dev/null 2>&1 || true
  F=$(grep -E "Max frequency for clock" "$OUT/pnr_$SEED.log" | tail -1 | sed -E 's/.*: ([0-9.]+) MHz.*/\1/')
  FMAXS="$FMAXS $F"
done
FMAX_BEST=$(echo $FMAXS | tr ' ' '\n' | sort -n | tail -1)
FMAX_AVG=$(echo $FMAXS | tr ' ' '\n' | awk '{s+=$1;n++} END{printf "%.2f", s/n}')

# ---------- 3. Gate-level simulation: function check + switching-activity proxy ----------
iverilog -g2012 -DGATE -DVCD='"'$OUT'/run.vcd"' -o "$OUT/gsim" tb/tb.v "$OUT/netlist.v"
SIMOUT=$(vvp "$OUT/gsim" | grep -E "RESULT|TRAP|TIMEOUT")
TOG=$(python3 scripts/toggles.py "$OUT/run.vcd" | tr -d '\n')
rm -f "$OUT/run.vcd"

echo "$V $CFG cells=$CELLS ffs=$FFS comb=$COMB depth=$DEPTH luts=$LUTS fmax_best=$FMAX_BEST fmax_avg=$FMAX_AVG fmax_all=[$FMAXS] | $SIMOUT | $TOG" | tee "results/$V-$CFG.txt"
