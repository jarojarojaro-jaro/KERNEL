#!/usr/bin/env python3
"""rocprofv3 kernel_trace.csv -> inputs for ashhart xray_trace.py / dispatch_audit.py.

Tokens are delimited by argmax_final_kernel (as in /tmp/ash-data/an.py); warm-up tokens skipped.
Per token: wall = end(argmax_i) -> end(argmax_{i+1}); gpu = sum of kernel durations (single queue,
checked non-overlapping); idle = wall - gpu, split into
  boundary gap  (argmax_final end -> next kernel start: token readback + host turn-around) -> host_sync_ms
  inner gaps    (between kernels inside the token)                                       -> enqueue_gap_ms
Bytes/visit from a user byte map (regex on "name gGRIDXxGRIDY" -> bytes), FLOPs = 2*weights.
Outputs: steps.jsonl (xray audit + dispatch audit-gaps), summary.csv (nsys cuda_gpu_kern_sum-like), gaps.txt.
"""
import csv, json, re, sys, collections, statistics

trace, outdir = sys.argv[1], sys.argv[2]
# (regex, bytes per launch, bytes per weight) -- user-supplied numbers, bytes ∝ grid for mv_q8p is [INFERENCE]
BYTEMAP = [
    (r"experts_q4k_gu_kernel.* g36864x8", 23.9e6, 0.5625),
    (r"experts_q50_down_kernel.* g73728x8", 14.6e6, 0.6875),
    (r"mv_q8p_kernel.* g6432768x1", 492e6, 1.0625),
    (r"mv_q8p_kernel.* g274432x1", 21.0e6, 1.0625),
    (r"mv_q8p_kernel.* g(\d+)x1", None, 1.0625),  # scale 21 MB by grid (assumes same K)
]


def short(n):
    n = n.replace("(anonymous namespace)::", "").replace("void ", "")
    return n.split("(")[0].replace("ik2::k::", "")


def bytes_for(key):
    for rx, b, bpw in BYTEMAP:
        m = re.search(rx, key)
        if m:
            if b is None:
                b = 21.0e6 * int(m.group(1)) / 274432
            return b, 2.0 * b / bpw
    return 0.0, 0.0


rows = list(csv.DictReader(open(trace)))
K = sorted((int(r["Start_Timestamp"]), int(r["End_Timestamp"]), short(r["Kernel_Name"]),
            r["Grid_Size_X"], r["Grid_Size_Y"]) for r in rows)
am = [i for i, k in enumerate(K) if "argmax_final" in k[2]]
am = am[6:-1]
steps, boundary_by_next, inner_after = [], collections.Counter(), collections.defaultdict(list)
tot = collections.defaultdict(lambda: [0, 0, 0.0, 0.0])
for a, b in zip(am, am[1:]):
    seg = K[a + 1:b + 1]
    wall = (K[b][1] - K[a][1]) / 1e6
    gpu = sum(e - s for s, e, *_ in seg) / 1e6
    bnd = (seg[0][0] - K[a][1]) / 1e6
    inner = 0.0
    for x, y in zip(seg, seg[1:]):
        g = y[0] - x[1]
        assert g >= 0, "overlapping kernels: multi-queue trace, union needed"
        inner += g / 1e6
        inner_after[x[2]].append(g / 1e3)
    boundary_by_next[seg[0][2]] += 1
    agg = collections.defaultdict(lambda: [0.0, 0, 0.0, 0.0])
    for s, e, n, gx, gy in seg:
        key = f"{n} g{gx}x{gy}"
        by, fl = bytes_for(key)
        v = agg[key]; v[0] += (e - s) / 1e6; v[1] += 1; v[2] += by; v[3] += fl
        t = tot[key]; t[0] += e - s; t[1] += 1; t[2] += by; t[3] += fl
    steps.append({"wall_ms": wall, "gpu_ms": gpu, "host_ms": 0.0, "idle_ms": wall - gpu,
                  "host_sync_ms": bnd, "enqueue_gap_ms": inner, "rows": 1,
                  "kernels": [{"name": k, "gpu_ms": v[0], "launches": v[1], "bytes": v[2], "flops": v[3]}
                              for k, v in agg.items()]})
with open(f"{outdir}/steps.jsonl", "w") as f:
    for s in steps:
        f.write(json.dumps(s) + "\n")
with open(f"{outdir}/summary.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Name", "Total Time (ns)", "Instances", "bytes", "flops"])
    for k, (ns, c, by, fl) in sorted(tot.items(), key=lambda x: -x[1][0]):
        w.writerow([k, ns, c, by, fl])
with open(f"{outdir}/gaps.txt", "w") as f:
    n = len(steps)
    f.write(f"tokens={n} wall_med={statistics.median(s['wall_ms'] for s in steps)*1e3:.1f}us "
            f"gpu_med={statistics.median(s['gpu_ms'] for s in steps)*1e3:.1f}us "
            f"boundary_med={statistics.median(s['host_sync_ms'] for s in steps)*1e3:.1f}us "
            f"inner_med={statistics.median(s['enqueue_gap_ms'] for s in steps)*1e3:.1f}us\n")
    f.write(f"first kernel after token boundary: {dict(boundary_by_next)}\n")
    f.write("inner gap AFTER kernel (us/token, n/token, median us):\n")
    for k, v in sorted(inner_after.items(), key=lambda x: -sum(x[1])):
        f.write(f"  {sum(v)/n:8.1f} {len(v)/n:6.1f} {statistics.median(v):6.2f}  {k}\n")
print(open(f"{outdir}/gaps.txt").read())
