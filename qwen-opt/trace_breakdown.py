#!/usr/bin/env python3
"""GPU time breakdown of a rocprofv3 kernel trace (steady-state part).

usage: trace_breakdown.py run_kernel_trace.csv [skip_fraction=0.3]
"""
import collections
import csv
import re
import sys

rows = list(csv.DictReader(open(sys.argv[1])))
rows.sort(key=lambda r: int(r["Start_Timestamp"]))
rows = rows[int(len(rows) * (float(sys.argv[2]) if len(sys.argv) > 2 else 0.3)):]
st = [int(r["Start_Timestamp"]) for r in rows]
en = [int(r["End_Timestamp"]) for r in rows]
busy = sum(e - s for s, e in zip(st, en))
wall = en[-1] - st[0]
print(f"kernels {len(rows)}  wall {wall/1e6:.1f} ms  busy {busy/1e6:.1f} ms  idle {100*(1-busy/wall):.1f}%")
cat = collections.Counter()
cnt = collections.Counter()
for r, s, e in zip(rows, st, en):
    n = r["Kernel_Name"]
    m = re.match(r"void mul_mat_vec_q<\(ggml_type\)(\d+), (\d+)", n)
    if m:
        k = f"mmvq n{m.group(2)}"
    elif "mul_mat_q<" in n:
        k = "mmq"
    elif "flash_attn" in n:
        k = "flash_attn"
    elif "gated_delta" in n:
        k = "gated_delta_net"
    elif "quantize" in n:
        k = "quantize_q8_1"
    elif "rms_norm" in n:
        k = "rms_norm"
    else:
        k = "other"
    cat[k] += e - s
    cnt[k] += 1
for k, v in cat.most_common():
    print(f"{k:16} {v/1e6:8.1f} ms {100*v/busy:5.1f}%  {cnt[k]:7d} launches")
