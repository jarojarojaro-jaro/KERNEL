#!/usr/bin/env python3
"""Step 5: pick the end-to-end candidate. Kernel time per variant = mean over the two micro passes; a candidate must be
lossless by construction, PASS test-backend-ops and have the md5 of VAR 0 (and VAR 0 the md5 of prod). Score = q4_0 KV
time at kv 131072 (the 255k fill averages ~128k depth). Writes res/BEST (the mask) or res/NONE, and res/select.txt."""
import collections, os, statistics, sys

D = os.path.expanduser("~/qwen-opt/fa-d256")
LOSSLESS = {1, 2, 3, 16, 19, 35, 51, 67, 83, 131, 147}
MIN_GAIN = 0.02  # kernel time at 131k must drop >= 2 % (FA ~53 % of the 255k fill -> ~+1 %; below that no e2e run)

t = collections.defaultdict(list)
for line in open(f"{D}/res/micro.txt"):
    p, v, typ, kv, us = line.split()
    t[(int(v), typ, int(kv))].append(float(us))
md5 = {}
for line in open(f"{D}/res/md5.txt"):
    f = line.split()
    md5[f[0]] = f[1]
tbo = {int(l.split()[0]): l.split()[1] for l in open(f"{D}/res/tbo.txt")}

out = []
variants = sorted({k[0] for k in t})
base = {k[1:]: statistics.mean(x) for k, x in t.items() if k[0] == 0}
out.append("var  " + "  ".join(f"{typ}@{kv//1024}k" for typ, kv in sorted(base)) + "   (us/run, Δ vs 0)  tbo md5")
for v in variants:
    cells = []
    for typ, kv in sorted(base):
        m = statistics.mean(t[(v, typ, kv)])
        cells.append(f"{m:9.0f} ({(m / base[(typ, kv)] - 1) * 100:+5.1f}%)")
    out.append(f"{v:3d}  " + "  ".join(cells) + f"   {tbo.get(v)} {md5.get(str(v), '-')}")
ref = md5.get("0")
out.append(f"prod md5 {md5.get('prod')} vs VAR 0 {ref}: {'SAME' if md5.get('prod') == ref else 'DIFFERENT'}")
cands = []
for v in variants:
    if v in LOSSLESS and tbo.get(v) == "PASS" and ref and md5.get(str(v)) == ref:
        cands.append((statistics.mean(t[(v, "q4_0", 131072)]) / base[("q4_0", 131072)], v))
cands.sort()
out.append("lossless candidates (time ratio @131k q4_0): " + ", ".join(f"{v}:{r:.3f}" for r, v in cands))
for f in ("BEST", "NONE"):
    if os.path.exists(f"{D}/res/{f}"):
        os.remove(f"{D}/res/{f}")
if cands and cands[0][0] <= 1 - MIN_GAIN and md5.get("prod") == ref:
    open(f"{D}/res/BEST", "w").write(f"{cands[0][1]}\n")
    out.append(f"BEST {cands[0][1]}")
else:
    open(f"{D}/res/NONE", "w").write("no lossless variant >= 2 % faster at 131k (or prod md5 != VAR 0)\n")
    out.append("NONE")
open(f"{D}/res/select.txt", "w").write("\n".join(out) + "\n")
print("\n".join(out))
