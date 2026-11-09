#!/usr/bin/env python3
"""Per-step GPU time of the decode phase from a rocprofv3 trace (--kernel-trace [--memory-copy-trace], csv) and the
lc.py lines of the same server run. The trace is cut at the prefill FA kernels (non-kvq flash_attn): the segments
between them with >= 50 kvq launches are the decode phases, matched in order to the requests (the last ones); the verify
steps come from the server timings (predicted_n - draft_n_accepted).

usage: prof_step.py TRACE_DIR LC_JSONL LABEL
"""
import csv, glob, json, sys
from collections import defaultdict


def load(trace_dir, kind):
    f = glob.glob(f"{trace_dir}/**/*{kind}.csv", recursive=True)
    return list(csv.DictReader(open(f[0]))) if f else []


def cat(name):
    if "flash_attn_ext_kvq" in name:
        return "kvq"
    if "combine" in name and "flash_attn" in name:
        return "comb"
    if "flash_attn" in name:
        return "fa_other"
    return "other"


def union(iv):
    tot, end = 0, -1
    for s, e in sorted(iv):
        if e <= end:
            continue
        tot += e - max(s, end)
        end = e
    return tot


def main():
    trace_dir, lc_file, label = sys.argv[1:4]
    ks = [(int(r["Start_Timestamp"]), int(r["End_Timestamp"]), r["Kernel_Name"], int(r["Workgroup_Size_Y"]),
           int(r["Grid_Size_X"])) for r in load(trace_dir, "kernel_trace")]
    ks.sort()
    cps = [(int(r["Start_Timestamp"]), int(r["End_Timestamp"]), r.get("Direction", ""), int(r.get("Size", 0) or 0))
           for r in load(trace_dir, "memory_copy_trace")]
    reqs = [json.loads(l) for l in open(lc_file) if json.loads(l)["label"] == label]
    segs, cur = [], []
    for k in ks:
        if cat(k[2]) == "fa_other":
            if cur:
                segs.append(cur)
            cur = []
        else:
            cur.append(k)
    if cur:
        segs.append(cur)
    segs = [s for s in segs if sum(cat(k[2]) == "kvq" for k in s) >= 50][-len(reqs):]
    if len(segs) != len(reqs):
        print(f"warning: {len(segs)} decode segments for {len(reqs)} requests")
    print(f"{'depth':>7} {'steps':>5} {'ms/step':>8} {'busy':>7} {'kvq':>7} {'comb':>6} {'fa_oth':>6} {'other':>7} "
          f"{'FA%busy':>7} {'h2d ms':>6} {'h2d MB':>7} {'kvq n/step':>10} {'2tile n/step':>12}")
    for q, seg in zip(reqs[-len(segs):] if segs else [], segs):
        # the segment holds the tail of the prefill and runs until the next request's first prefill FA: the decode
        # window starts at its first kvq launch and ends after its last one, at the first idle gap > 50 ms (end of the
        # request; decode steps are a few ms apart at most)
        idx = [i for i, k in enumerate(seg) if cat(k[2]) == "kvq"]
        end = idx[-1] + 1
        while end < len(seg) and seg[end][0] - seg[end - 1][1] <= 50_000_000:
            end += 1
        dec = seg[idx[0]:end]
        steps = max(1, q["steps"])
        span = dec[-1][1] - dec[0][0]
        t = defaultdict(int)
        n_kvq = n_2t = 0
        for s, e, name, wgy, gx in dec:
            c = cat(name)
            t[c] += e - s
            if c == "kvq":
                n_kvq += 1
                # verify with >= 2 Q tiles: grid x >= 64 threads (2 blocks of 32) or the ONCE kernel (16 warps)
                n_2t += gx >= 64 or wgy == 16
        busy = union([(k[0], k[1]) for k in dec])
        h2d = [(s, e, sz) for s, e, d, sz in cps if dec[0][0] <= s <= dec[-1][1] and "HOST_TO_DEVICE" in d.upper()]
        ms = lambda ns: ns / 1e6 / steps
        fa = t["kvq"] + t["comb"]
        print(f"{q['depth']:>7} {steps:>5} {ms(span):8.2f} {ms(busy):7.2f} {ms(t['kvq']):7.2f} {ms(t['comb']):6.2f} "
              f"{ms(t['fa_other']):6.2f} {ms(t['other']):7.2f} {100 * fa / max(1, busy):6.1f}% "
              f"{ms(sum(e - s for s, e, _ in h2d)):6.3f} {sum(sz for *_, sz in h2d) / 1e6 / steps:7.3f} "
              f"{n_kvq / steps:10.1f} {n_2t / steps:12.1f}")


if __name__ == "__main__":
    main()
