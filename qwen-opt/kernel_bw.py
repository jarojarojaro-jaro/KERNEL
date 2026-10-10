#!/usr/bin/env python3
"""Effective DRAM bandwidth of mul_mat_vec_q per quant type during decode.

bytes/token per type come from the GGUF (all 2D weights except token_embd and
the MTP block, which plain decode does not read); time per type comes from a
rocprofv3 kernel_stats.csv. n_tokens = number of forward passes in the trace.

Usage: kernel_bw.py MODEL.gguf kernel_stats.csv N_FORWARD_PASSES
"""
import collections
import csv
import re
import sys

import gguf

PEAK = 960e9
model, stats, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
r = gguf.GGUFReader(model)
nblk = int(r.fields["qwen35.block_count"].contents())
nextn = int(r.fields.get("qwen35.nextn_predict_layers").contents() or 0)
mtp_blocks = {f"blk.{i}." for i in range(nblk - nextn, nblk)}
by_type: dict[int, int] = collections.Counter()
for t in r.tensors:
    if t.name == "token_embd.weight" or any(t.name.startswith(b) for b in mtp_blocks):
        continue
    if len(t.shape) < 2 or t.shape[1] == 1:
        continue
    by_type[int(t.tensor_type)] += int(t.n_bytes)

tm: dict[int, float] = collections.Counter()
other = 0.0
for row in csv.DictReader(open(stats)):
    m = re.match(r"void mul_mat_vec_q<\(ggml_type\)(\d+)", row["Name"])
    if m:
        tm[int(m.group(1))] += float(row["TotalDurationNs"])
    else:
        other += float(row["TotalDurationNs"])

tot = sum(tm.values()) + other
print(f"{'type':8} {'GB/tok':>7} {'ms/tok':>7} {'GB/s':>7} {'%peak':>6} {'%time':>6}")
for ty, ns in sorted(tm.items(), key=lambda kv: -kv[1]):
    b = by_type.get(ty, 0)
    s = ns / 1e9
    bw = b * n / s if s else 0
    print(f"{gguf.GGMLQuantizationType(ty).name:8} {b/1e9:7.3f} {ns/1e6/n:7.3f} {bw/1e9:7.0f} "
          f"{100*bw/PEAK:6.1f} {100*ns/tot:6.1f}")
allb = sum(by_type[t] for t in tm)
print(f"mmvq total: {allb/1e9:.2f} GB/tok, {sum(tm.values())/1e6/n:.2f} ms/tok, "
      f"{allb*n/(sum(tm.values())/1e9)/1e9:.0f} GB/s")
print(f"non-mmvq: {other/1e6/n:.2f} ms/tok; total GPU {tot/1e6/n:.2f} ms/tok "
      f"-> {1000/(tot/1e6/n):.1f} tok/s if no gaps")
