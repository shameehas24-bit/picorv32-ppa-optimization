#!/usr/bin/env python3
"""Read results/*.txt written by run_flow.sh and print an evaluator-friendly report.
Also saves ppa_report.png (needs matplotlib; skipped with a note if missing)."""
import re, glob, os

rows = {}
for f in glob.glob(os.path.join(os.path.dirname(__file__), "..", "results", "*.txt")):
    t = open(f).read()
    m = re.match(r"(\w+) (\w+) ", t)
    if not m or m.group(1) not in ("orig", "opt"):
        continue
    g = lambda k: float(re.search(k + r"=([0-9.]+)", t).group(1))
    rows[(m.group(1), m.group(2))] = dict(
        cells=g("cells"), luts=g("luts"), depth=g("depth"), fmax=g("fmax_avg"), tpc=g("tpc"),
        result=re.search(r"RESULT=(\w+) HASH=(\w+) CYCLES=(\d+)", t).groups())

def pct(a, b):
    return (b - a) / a * 100

print("=" * 78)
print(" PicoRV32 PPA study: original vs optimized RTL (same tools, same benchmark)")
print("=" * 78)
for cfg, label in (("default", "Default config"), ("barrel", "Barrel-shifter config")):
    if ("orig", cfg) not in rows or ("opt", cfg) not in rows:
        print(f"\n[{label}] results missing - run: bash scripts/run_flow.sh orig {cfg} / opt {cfg}")
        continue
    o, p = rows[("orig", cfg)], rows[("opt", cfg)]
    print(f"\n{label}")
    print(f"  {'Metric':<28}{'Original':>11}{'Optimized':>11}{'Change':>10}")
    for name, key, fmt in (("Gate cells (area)", "cells", "{:.0f}"), ("iCE40 LUTs (area)", "luts", "{:.0f}"),
                           ("Logic depth (timing)", "depth", "{:.0f}"), ("Fmax avg MHz (timing)", "fmax", "{:.1f}"),
                           ("Toggles/cycle (power proxy)", "tpc", "{:.1f}")):
        print(f"  {name:<28}{fmt.format(o[key]):>11}{fmt.format(p[key]):>11}{pct(o[key], p[key]):>+9.1f}%")
    same = o["result"] == p["result"]
    print(f"  Functional check: {'PASS - identical result, memory hash and cycle count' if same else 'FAIL - outputs differ'}"
          f"  (RESULT={o['result'][0]} CYCLES={o['result'][2]})")
print("\nNotes: Fmax varies about +/-4 MHz between placement seeds. Power is a switching-activity")
print("proxy from gate-level simulation, not measured power.")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cfgs = [c for c in ("default", "barrel") if ("orig", c) in rows and ("opt", c) in rows]
    metrics = (("luts", "iCE40 LUTs (lower is better)"), ("cells", "Gate cells (lower is better)"),
               ("fmax", "Fmax, MHz (higher is better)"))
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4))
    for ax, (key, title) in zip(axes, metrics):
        w = 0.35
        for i, (v, col) in enumerate((("orig", "#9fb0b2"), ("opt", "#7fa88a"))):
            vals = [rows[(v, c)][key] for c in cfgs]
            bars = ax.bar([x + (i - 0.5) * w for x in range(len(cfgs))], vals, w, color=col,
                          label="Original" if v == "orig" else "Optimized")
            for b, val in zip(bars, vals):
                ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{val:.0f}" if key != "fmax" else f"{val:.1f}",
                        ha="center", va="bottom", fontsize=9)
        ax.set_xticks(range(len(cfgs)))
        ax.set_xticklabels(cfgs)
        ax.set_title(title, fontsize=11)
        ax.margins(y=0.12)
    axes[0].legend()
    fig.suptitle("PicoRV32 PPA: original vs optimized RTL", fontsize=13)
    plt.tight_layout()
    out = os.path.join(os.path.dirname(__file__), "..", "ppa_report.png")
    plt.savefig(out, dpi=200)
    print("\nSaved chart:", os.path.normpath(out))
except ImportError:
    print("\n(matplotlib not installed: run 'pip install matplotlib' to get ppa_report.png)")
