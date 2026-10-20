#!/usr/bin/env python3
"""ABBA stats for report 31: abba.py <spec_sweep.jsonl|copy_bench.jsonl> <A1> <B1> <B2> <A2>
Per pass p (A1/B1, A2/B2) and prompt: ratio B/A of t/s, ms/step, tok/step. Prints pooled t/s per arm (tokens/ms over
all prompts), mean ratio with a t-based 95% CI over the 2 x n_prompts paired ratios."""
import json
import math
import statistics
import sys

f, a1, b1, b2, a2 = sys.argv[1:6]
rows = {}
for line in open(f):
    r = json.loads(line)
    rows[r["label"]] = r  # last row per label wins


def pooled(lbl):
    p = rows[lbl]["prompts"]
    return statistics.median(v["tps"] for v in p.values()), statistics.median(v["ms_step"] for v in p.values()), \
        statistics.median(v["tok_step"] for v in p.values())


for lbl in (a1, b1, b2, a2):
    m = pooled(lbl)
    print(f"{lbl:28s} median t/s {m[0]:7.2f}  ms/step {m[1]:7.2f}  tok/step {m[2]:5.2f}")
T = {0.975: {2: 12.71, 3: 4.30, 4: 3.18, 5: 2.78, 6: 2.57, 7: 2.45, 8: 2.36, 9: 2.31, 10: 2.26, 11: 2.23, 12: 2.20}}
for key in ("tps", "ms_step", "tok_step"):
    rs = []
    for A, B in ((a1, b1), (a2, b2)):
        pa, pb = rows[A]["prompts"], rows[B]["prompts"]
        rs += [pb[k][key] / pa[k][key] for k in pa if k in pb]
    n = len(rs)
    mu = statistics.mean(rs)
    sd = statistics.stdev(rs) if n > 1 else 0.0
    t = T[0.975].get(n - 1, 2.0)
    h = t * sd / math.sqrt(n)
    print(f"B/A {key:8s}: {100*(mu-1):+6.2f}%  CI95 [{100*(mu-h-1):+6.2f}, {100*(mu+h-1):+6.2f}]  (n={n})")
