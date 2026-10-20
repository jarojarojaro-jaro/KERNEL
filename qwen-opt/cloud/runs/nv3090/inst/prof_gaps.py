#!/usr/bin/env python3
"""Gap attribution for an nsys sqlite export (nv-3090, 2026-10-20): GPU idle gaps in [lo, hi) us grouped by
(previous kernel, next kernel), plus MMVQ launches grouped by grid/block with mean duration, and the number of
'steps' (launches of the largest-grid MMVQ = the LM head of the verify).
usage: prof_gaps.py <file.sqlite> [lo_us=20] [hi_us=1000]
"""
import sqlite3
import sys
from collections import defaultdict

db = sqlite3.connect(sys.argv[1])
lo = float(sys.argv[2]) if len(sys.argv) > 2 else 20.0
hi = float(sys.argv[3]) if len(sys.argv) > 3 else 1000.0
names = dict(db.execute("select id, value from StringIds"))
rows = db.execute("select start, end, shortName, gridX, gridY, gridZ, blockX, blockY, graphNodeId, registersPerThread from "
                  "CUPTI_ACTIVITY_KIND_KERNEL order by start").fetchall()
mem = db.execute("select start, end, copyKind, bytes from CUPTI_ACTIVITY_KIND_MEMCPY order by start").fetchall()
ev = sorted([(s, e, names.get(n, "?"), g) for s, e, n, gx, gy, gz, bx, by, g, rg in rows] +
            [(s, e, f"memcpy{k}:{b}", None) for s, e, k, b in mem])
pairs = defaultdict(lambda: [0, 0.0])
cur_e = ev[0][1]
prev = ev[0]
for x in ev[1:]:
    gap = (x[0] - cur_e) / 1e3
    if lo <= gap < hi:
        key = (prev[2][:40], "g" if prev[3] else "-", x[2][:40], "g" if x[3] else "-")
        pairs[key][0] += 1
        pairs[key][1] += gap
    if x[1] > cur_e:
        cur_e = x[1]
        prev = x
print(f"gaps {lo}-{hi} us by (prev kernel, in-graph?, next kernel, in-graph?):")
for k, (n, t) in sorted(pairs.items(), key=lambda z: -z[1][1])[:30]:
    print(f"  {n:6d} {t/1e3:8.2f} ms  {k}")
mm = defaultdict(lambda: [0, 0])
eager = collections_eager = {}
for s, e, n, gx, gy, gz, bx, by, g, rg in rows:
    if g is None:
        eager[names.get(n, "?")] = eager.get(names.get(n, "?"), 0) + 1
    if names.get(n, "") == "mul_mat_vec_q":
        mm[(gx, gy, gz, bx, by, rg)][0] += 1
        mm[(gx, gy, gz, bx, by, rg)][1] += e - s
print("eager (non-graph) kernels:", sum(eager.values()), sorted(eager.items(), key=lambda z: -z[1])[:15])
print("mul_mat_vec_q by grid (gx,gy,gz,bx,by,regs): n, mean us, total ms")
for k, (n, t) in sorted(mm.items(), key=lambda z: -z[1][1])[:30]:
    print(f"  {str(k):32s} {n:7d} {t/n/1e3:9.1f} {t/1e6:9.1f}")
big = max(mm, key=lambda k: k[0] * k[1] * k[2])
print("largest-grid MMVQ (LM head proxy):", big, mm[big][0], "launches")
