#!/usr/bin/env python3
"""Time ledger from rocprofv3 kernel stats: us/token per kernel (normalized by tokens), share, calls/token; with a second
stats file: delta per kernel. usage: ledger.py STATS.csv TOKENS [BASE_STATS.csv BASE_TOKENS] [--top 25]"""
import csv, sys, re
def load(p, n):
    d = {}
    for r in csv.DictReader(open(p)):
        k = re.sub(r'^void ', '', r['Name']).replace('(anonymous namespace)::', ''); k = re.split(r'[<(]', k)[0][:110]
        t, c = d.get(k, (0.0, 0))
        d[k] = (t + float(r['TotalDurationNs']) / 1e3 / n, c + int(r['Calls']) / n)
    return d
a = sys.argv[1:]; top = 25
if '--top' in a: i = a.index('--top'); top = int(a[i + 1]); del a[i:i + 2]
cur = load(a[0], float(a[1])); base = load(a[2], float(a[3])) if len(a) >= 4 else None
tot = sum(v[0] for v in cur.values())
print(f"GPU time per token: {tot:.1f} us" + (f" (base {sum(v[0] for v in base.values()):.1f} us)" if base else ""))
print(f"{'us/tok':>8} {'share':>6} {'calls/tok':>9} {'delta':>8}  kernel")
keys = sorted(set(cur) | set(base or {}), key=lambda k: -cur.get(k, (0, 0))[0])
for k in keys[:top]:
    t, c = cur.get(k, (0.0, 0)); dt = '' if not base else f"{t - base.get(k, (0.0, 0))[0]:+8.1f}"
    print(f"{t:8.1f} {t / tot * 100:5.1f}% {c:9.1f} {dt:>8}  {k}")
