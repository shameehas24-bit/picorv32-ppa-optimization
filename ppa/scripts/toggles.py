#!/usr/bin/env python3
"""Count bit-level toggles of every net in the DUT scope of a VCD file.

Switching activity is a standard first-order proxy for dynamic power
(P_dyn ~ alpha * C * V^2 * f). Here every net is weighted equally, so the
number is relative, not absolute: use it to compare variants on the same workload.
Prints: toggles=<total> cycles=<clock cycles> tpc=<toggles per cycle>
"""
import sys

def main(path):
    ids = {}          # id -> (name, width)
    last = {}         # id -> last value string
    total = 0
    clk_id = None
    cycles = 0
    skip = {"clk", "resetn"}
    skip_ids = set()
    in_defs = True
    with open(path) as f:
        for line in f:
            if in_defs:
                if line.startswith("$var"):
                    p = line.split()
                    width, vid, name = int(p[2]), p[3], p[4]
                    ids[vid] = (name, width)
                    if name == "clk":
                        clk_id = vid
                    if name in skip:
                        skip_ids.add(vid)
                elif line.startswith("$enddefinitions"):
                    in_defs = False
                continue
            line = line.strip()
            if not line or line[0] in "#$":
                continue
            if line[0] in "01xzXZ":
                val, vid = line[0], line[1:]
            elif line[0] in "bB":
                val, vid = line[1:].split()
            else:
                continue
            if vid == clk_id:
                if val == "1" and last.get(vid) == "0":
                    cycles += 1
                last[vid] = val
                continue
            if vid in skip_ids or vid not in ids:
                continue
            prev = last.get(vid)
            last[vid] = val
            if prev is None or prev == val:
                continue
            w = ids[vid][1]
            if w == 1:
                if prev in "01" and val in "01":
                    total += 1
            else:
                a = prev.rjust(w, "0" if prev[0] != "x" else "x")
                b = val.rjust(w, "0" if val[0] != "x" else "x")
                total += sum(1 for x, y in zip(a, b) if x != y and x in "01" and y in "01")
    print("toggles=%d cycles=%d tpc=%.2f" % (total, cycles, total / max(cycles, 1)))

if __name__ == "__main__":
    main(sys.argv[1])
