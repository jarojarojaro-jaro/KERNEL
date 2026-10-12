#!/usr/bin/env python3
"""Per-speculative-step kernel statistics of a rocprofv3 kernel trace.

A verify graph is a burst of >= MIN_VERIFY kernels with inter-kernel gaps < BURST_GAP_US.
A step runs from the start of one verify burst to the start of the next.
Reports medians: kernels/step, verify kernels, verify gap sum (sum of start[i]-end[i-1] inside the burst),
verify wall, step wall, and the top kernel names of a median verify.

usage: steps.py run_kernel_trace.csv [--names]
"""
import collections
import csv
import statistics
import sys

BURST_GAP_US = 60.0
MIN_VERIFY = 500

rows = list(csv.DictReader(open(sys.argv[1])))
rows.sort(key=lambda r: int(r["Start_Timestamp"]))
st = [int(r["Start_Timestamp"]) / 1000.0 for r in rows]  # us
en = [int(r["End_Timestamp"]) / 1000.0 for r in rows]
names = [r["Kernel_Name"] for r in rows]

# bursts
bursts = []
b0 = 0
for i in range(1, len(rows)):
    if st[i] - en[i - 1] > BURST_GAP_US:
        bursts.append((b0, i))
        b0 = i
bursts.append((b0, len(rows)))
verify = [b for b in bursts if b[1] - b[0] >= MIN_VERIFY]

# drop the first verify bursts (prompt processing / warmup) and the last (end of generation)
verify = verify[2:-1] if len(verify) > 4 else verify

per = []
for (a, b), nxt in zip(verify, verify[1:] + [None]):
    gaps = sum(max(0.0, st[i] - en[i - 1]) for i in range(a + 1, b))
    busy = sum(en[i] - st[i] for i in range(a, b))
    rec = {"vk": b - a, "vgap": gaps, "vwall": en[b - 1] - st[a], "vbusy": busy}
    if nxt is not None:
        rec["sk"] = nxt[0] - a
        rec["swall"] = st[nxt[0]] - st[a]
    per.append(rec)

def med(k):
    v = [p[k] for p in per if k in p]
    return statistics.median(v) if v else float("nan")

print(f"verify bursts {len(per)}: kernels/step {med('sk'):.0f}  verify kernels {med('vk'):.0f}  "
      f"verify gap {med('vgap')/1000:.2f} ms  verify busy {med('vbusy')/1000:.2f} ms  verify wall {med('vwall')/1000:.2f} ms  "
      f"step wall {med('swall')/1000:.2f} ms")

if "--names" in sys.argv:
    # kernel name histogram of the median-sized verify burst
    target = med("vk")
    a, b = min(verify, key=lambda ab: abs((ab[1] - ab[0]) - target))
    c = collections.Counter()
    t = collections.Counter()
    for i in range(a, b):
        n = names[i].split("(")[0][:110]
        c[n] += 1
        t[n] += en[i] - st[i]
    for n, k in c.most_common(60):
        print(f"{k:5d} {t[n]:9.1f} us  {n}")
