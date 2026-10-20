#!/usr/bin/env python3
"""MMVQ breakdown of an nsys sqlite (report 31): group mul_mat_vec_q launches by (template args, grid), per step.
usage: prof_mmvq.py <file.sqlite> <steps> [--top N]"""
import collections
import re
import sqlite3
import sys

db, steps = sys.argv[1], int(sys.argv[2])
top = int(sys.argv[4]) if len(sys.argv) > 4 else 40
c = sqlite3.connect(db)
names = dict(c.execute("select id, value from StringIds"))
rows = c.execute("select start, end, demangledName, shortName, gridX, gridY, gridZ, blockX, blockY from CUPTI_ACTIVITY_KIND_KERNEL").fetchall()
agg = collections.defaultdict(lambda: [0, 0])
tot = collections.defaultdict(int)
for s, e, dn, sn, gx, gy, gz, bx, by in rows:
    n = names.get(sn, "")
    if "mul_mat_vec_q" not in n:
        continue
    d = names.get(dn, "")
    m = re.search(r"mul_mat_vec_q<([^>]*)>", d)
    targs = m.group(1) if m else d[:80]
    targs = re.sub(r"\(ggml_type\)", "t", targs)
    key = (targs[:70], f"{gx}x{gy}x{gz}", f"{bx}x{by}")
    agg[key][0] += e - s
    agg[key][1] += 1
all_t = sum(v[0] for v in agg.values())
print(f"mmvq total {all_t/1e6/steps:.2f} ms/step")
print(f"{'ms/step':>8} {'n/step':>7} {'us/call':>8}  template | grid | block")
for k, (t, n) in sorted(agg.items(), key=lambda x: -x[1][0])[:top]:
    print(f"{t/1e6/steps:8.3f} {n/steps:7.1f} {t/1e3/n:8.1f}  {k[0]} | {k[1]} | {k[2]}")
