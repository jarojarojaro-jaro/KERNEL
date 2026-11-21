#!/usr/bin/env python3
"""K-033: summary of dpm_poll.sh files: per file the samples under load (gpu_busy >= 50 %) and idle, the share of each
MCLK/FCLK level, SCLK median/p10/p90 under load, and the peak VRAM. usage: dpm_sum.py FILE..."""
import collections, statistics, sys

for path in sys.argv[1:]:
    rows = []
    for line in open(path):
        p = line.split()
        if len(p) == 6 and all(x.lstrip("-").replace(".", "").isdigit() for x in p):
            rows.append([float(p[0])] + [int(x) for x in p[1:]])
    if not rows:
        print(f"{path}: no samples"); continue
    load = [r for r in rows if r[4] >= 50]
    print(f"{path}: {len(rows)} samples over {rows[-1][0] - rows[0][0]:.0f} s, {len(load)} under load (busy >= 50 %), "
          f"peak VRAM {max(r[5] for r in rows)} MiB")
    for name, sel in (("load", load), ("idle", [r for r in rows if r[4] < 50])):
        if not sel:
            continue
        sc = sorted(r[1] for r in sel)
        q = lambda f: sc[min(len(sc) - 1, int(f * len(sc)))]
        lv = lambda i: ", ".join(f"{k} MHz {100 * v / len(sel):.0f}%" for k, v in sorted(collections.Counter(r[i] for r in sel).items()))
        print(f"  {name}: sclk median {statistics.median(sc):.0f} (p10 {q(0.1)}, p90 {q(0.9)}) MHz | mclk {lv(2)} | fclk {lv(3)}")
