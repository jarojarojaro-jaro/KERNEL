#!/usr/bin/env python3
"""Host-side drilldown of an nsys sqlite export (nv-3090, 2026-10-20).

1) percentiles of every CUDA API call duration (graph launch, sync, memcpy, kernel launch);
2) for GPU idle gaps >= LO us that end in a graph kernel: which runtime API calls overlap the gap (by name, total
   overlap), i.e. what the host was doing while the GPU waited;
3) osrt (pthread/ioctl/poll...) calls overlapping those gaps, if traced.
usage: prof_host.py <file.sqlite> [lo_us=50]
"""
import sqlite3
import sys
from bisect import bisect_left
from collections import defaultdict

db = sqlite3.connect(sys.argv[1])
lo = float(sys.argv[2]) * 1e3 if len(sys.argv) > 2 else 50e3
names = dict(db.execute("select id, value from StringIds"))
api = db.execute("select start, end, nameId from CUPTI_ACTIVITY_KIND_RUNTIME order by start").fetchall()
d = defaultdict(list)
for s, e, n in api:
    d[names.get(n, "?")].append(e - s)
print("API call durations (us): n p50 p90 p99 max total_ms")
for k, v in sorted(d.items(), key=lambda z: -sum(z[1]))[:12]:
    v.sort()
    q = lambda f: v[min(len(v) - 1, int(f * len(v)))] / 1e3
    print(f"  {k:40s} {len(v):7d} {q(.5):8.1f} {q(.9):8.1f} {q(.99):8.1f} {v[-1]/1e3:9.1f} {sum(v)/1e6:9.1f}")
kern = db.execute("select start, end, graphNodeId from CUPTI_ACTIVITY_KIND_KERNEL order by start").fetchall()
mem = db.execute("select start, end from CUPTI_ACTIVITY_KIND_MEMCPY order by start").fetchall()
ev = sorted([(s, e, g is not None) for s, e, g in kern] + [(s, e, False) for s, e in mem])
gaps = []
cur = ev[0][1]
for s, e, g in ev[1:]:
    if s - cur >= lo:
        gaps.append((cur, s, g))
    cur = max(cur, e)
print(f"gaps >= {lo/1e3:.0f} us: {len(gaps)}, total {sum(b - a for a, b, _ in gaps)/1e6:.1f} ms; "
      f"ending in graph kernel: {sum(1 for *_, g in gaps if g)}")
starts = [a[0] for a in api]
ov = defaultdict(float)
for a, b, g in gaps:
    i = max(0, bisect_left(starts, a) - 50)
    while i < len(api) and api[i][0] < b:
        s, e, n = api[i]
        o = min(e, b) - max(s, a)
        if o > 0:
            ov[names.get(n, "?")] += o
        i += 1
tot = sum(b - a for a, b, _ in gaps)
print("runtime API time overlapping those gaps (ms, % of gap time):")
for k, v in sorted(ov.items(), key=lambda z: -z[1])[:12]:
    print(f"  {k:40s} {v/1e6:8.2f} {100*v/tot:5.1f}%")
try:
    osrt = db.execute("select start, end, nameId from OSRT_API order by start").fetchall()
except sqlite3.OperationalError:
    osrt = []
if osrt:
    st = [x[0] for x in osrt]
    ov = defaultdict(float)
    for a, b, g in gaps:
        i = max(0, bisect_left(st, a) - 50)
        while i < len(osrt) and osrt[i][0] < b:
            s, e, n = osrt[i]
            o = min(e, b) - max(s, a)
            if o > 0:
                ov[names.get(n, "?")] += o
            i += 1
    print("OS runtime calls overlapping the gaps (ms; all threads, may exceed gap time):")
    for k, v in sorted(ov.items(), key=lambda z: -z[1])[:10]:
        print(f"  {k:40s} {v/1e6:8.2f}")
