#!/usr/bin/env python3
"""Summarize an nsys sqlite export of a llama-server decode run (report 31, 4060 Ti).

usage: prof.py <file.sqlite> [--steps N] [--skip-s S]
Window = from the first kernel after --skip-s seconds (default: last 60% of the trace, skips load + prefill) to the
last kernel. Prints: wall, GPU busy (merged kernel intervals), idle, top kernels by total time, gap histogram,
runtime API counts (graph launches, syncs, memcpy). --steps N divides per-step numbers.
"""
import argparse
import collections
import sqlite3

ap = argparse.ArgumentParser()
ap.add_argument("db")
ap.add_argument("--steps", type=int, default=0)
ap.add_argument("--skip-s", type=float, default=-1.0)
ap.add_argument("--top", type=int, default=30)
a = ap.parse_args()
c = sqlite3.connect(a.db)
names = dict(c.execute("select id, value from StringIds"))
ks = c.execute("select start, end, coalesce(demangledName, shortName), shortName from CUPTI_ACTIVITY_KIND_KERNEL order by start").fetchall()
t0, t1 = ks[0][0], ks[-1][1]
lo = t0 + int(a.skip_s * 1e9) if a.skip_s >= 0 else t0 + int(0.4 * (t1 - t0))
ks = [k for k in ks if k[0] >= lo]
w0, w1 = ks[0][0], ks[-1][1]
busy = 0
cur_s, cur_e = ks[0][0], ks[0][1]
gaps = []
for s, e, _, _ in ks[1:]:
    if s > cur_e:
        busy += cur_e - cur_s
        gaps.append(s - cur_e)
        cur_s, cur_e = s, e
    else:
        cur_e = max(cur_e, e)
busy += cur_e - cur_s
wall = w1 - w0
st = a.steps or 1
print(f"window {wall/1e6:.1f} ms, kernels {len(ks)}, busy {busy/1e6:.1f} ms ({100*busy/wall:.1f}%), idle {(wall-busy)/1e6:.1f} ms")
if a.steps:
    print(f"per step: wall {wall/1e6/st:.2f} ms, busy {busy/1e6/st:.2f} ms, idle {(wall-busy)/1e6/st:.2f} ms, kernels {len(ks)/st:.0f}")
agg = collections.defaultdict(lambda: [0, 0])
for s, e, dn, sn in ks:
    n = names.get(sn, str(sn))
    agg[n][0] += e - s
    agg[n][1] += 1
print(f"\n{'ms/step':>8} {'%busy':>6} {'n/step':>7} {'us/call':>8}  kernel")
for n, (t, cnt) in sorted(agg.items(), key=lambda x: -x[1][0])[: a.top]:
    print(f"{t/1e6/st:8.3f} {100*t/busy:6.1f} {cnt/st:7.1f} {t/1e3/cnt:8.1f}  {n[:110]}")
hist = collections.Counter()
big = 0
for g in gaps:
    b = "<2us" if g < 2e3 else "<5us" if g < 5e3 else "<20us" if g < 2e4 else "<100us" if g < 1e5 else "<1ms" if g < 1e6 else ">=1ms"
    hist[b] += g
print("\ngap time by size (ms/step):", {k: round(v / 1e6 / st, 3) for k, v in sorted(hist.items())})
big = sorted(gaps)[-10:]
print("largest gaps us:", [round(g / 1e3) for g in big])
try:
    rt = c.execute("select nameId, count(*), sum(end-start) from CUPTI_ACTIVITY_KIND_RUNTIME where start >= ? group by nameId", (lo,)).fetchall()
    print("\nruntime API (per step count, ms/step):")
    for nid, cnt, tot in sorted(rt, key=lambda x: -x[2])[:15]:
        print(f"  {names.get(nid, nid)[:60]:60s} {cnt/st:8.1f} {tot/1e6/st:8.3f}")
except sqlite3.OperationalError as e:
    print("no runtime table", e)
