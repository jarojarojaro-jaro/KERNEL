#!/usr/bin/env python3
"""K-111 (CPU, existing trace): per-kernel-name GPU time per verify step in the 1.7k decode segment of a rocprofv3 run
(kvq-once run-1107-2315 prof-N0 = topka-q63 + kvq-once ONCE=0, PM4 off). Segmentation as prof_step.py."""
import csv, glob, gzip, json, re, sys
from collections import defaultdict
d, lc, label = sys.argv[1:4]
f = glob.glob(f"{d}/**/*kernel_trace.csv*", recursive=True)[0]
op = gzip.open if f.endswith(".gz") else open
ks = sorted((int(r["Start_Timestamp"]), int(r["End_Timestamp"]), r["Kernel_Name"], int(r["Grid_Size_X"]), int(r["Grid_Size_Y"]))
            for r in csv.DictReader(op(f, "rt")))
reqs = [json.loads(l) for l in open(lc) if json.loads(l)["label"] == label]
cat = lambda n: "fa_other" if ("flash_attn" in n and "kvq" not in n and "combine" not in n) else "x"
segs, cur = [], []
for k in ks:
    if cat(k[2]) == "fa_other":
        if cur: segs.append(cur)
        cur = []
    else: cur.append(k)
if cur: segs.append(cur)
segs = [s for s in segs if sum("flash_attn_ext_kvq" in k[2] for k in s) >= 50][-len(reqs):]
seg, req = segs[0], reqs[0]
steps = req["n"] - req.get("acc", req.get("draft_n_accepted", 0)) if "n" in req else None
print("request keys:", list(req.keys())[:12])
def short(n):
    n = re.sub(r"\(.*", "", n); n = re.sub(r"void ", "", n)
    return n[:110]
by = defaultdict(lambda: [0, 0])
for s, e, n, gx, gy in seg:
    by[short(n)][0] += (e - s); by[short(n)][1] += 1
tot = sum(v[0] for v in by.values()); wall = seg[-1][1] - seg[0][0]
print(f"segment kernels {len(seg)}, busy {tot/1e6:.1f} ms, wall {wall/1e6:.1f} ms")
for n, (t, c) in sorted(by.items(), key=lambda x: -x[1][0])[:40]:
    print(f"{t/1e6:9.2f} ms {100*t/tot:5.1f}% {c:7d}  {n}")
