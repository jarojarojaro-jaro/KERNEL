#!/usr/bin/env python3
"""Report 58: chat (spec_sweep.py) ABBA summary. ARM = label without PREFIX and the trailing repeat letter a-d.
Per arm: per-prompt t/s and tok/step averaged over its instances, median over prompts; B vs A: per-prompt t/s ratio
(geometric mean, 95% bootstrap CI over prompts); A drift = first vs last A instance (geometric mean of prompt ratios).

usage: spec_sum.py spec_sweep.jsonl PREFIX [BASE=A]
"""
import collections
import json
import math
import random
import re
import statistics
import sys


def arm_of(label, prefix):
    return re.sub(r"(?<=[0-9A-Za-z])[a-d]$", "", label[len(prefix):])


def gmean(xs):
    return math.exp(sum(math.log(x) for x in xs) / len(xs))


def main():
    path, prefix = sys.argv[1], sys.argv[2]
    base = sys.argv[3] if len(sys.argv) > 3 else "A"
    inst = collections.defaultdict(list)  # arm -> [(label, prompts)]
    for line in open(path):
        if not line.strip():
            continue
        r = json.loads(line)
        if r["label"].startswith(prefix) and r["temp"] == 1.0:
            inst[arm_of(r["label"], prefix)].append((r["label"], r["prompts"]))
    if base not in inst:
        sys.exit(f"no rows of base arm {base!r} under prefix {prefix!r}")
    per = {}
    for arm, rows in inst.items():
        names = sorted(set.intersection(*(set(p) for _, p in rows)))
        tps = {n: statistics.mean(p[n]["tps"] for _, p in rows) for n in names}
        tok = {n: statistics.mean(p[n]["tok_step"] for _, p in rows) for n in names}
        per[arm] = (tps, tok)
        print(f"{arm}: {len(rows)} instances ({', '.join(l for l, _ in rows)}), median {statistics.median(tps.values()):.1f} t/s, "
              f"median {statistics.median(tok.values()):.3f} tok/step")
    a_rows = inst[base]
    if len(a_rows) >= 2:
        first, last = a_rows[0][1], a_rows[-1][1]
        common = [n for n in first if n in last]
        d = gmean([last[n]["tps"] / first[n]["tps"] for n in common]) - 1
        print(f"{base} drift (first -> last instance): {100 * d:+.2f}%{'  INVALID (> 1%)' if abs(d) > 0.01 else ''}")
    for arm in per:
        if arm == base:
            continue
        names = [n for n in per[arm][0] if n in per[base][0]]
        ratios = [per[arm][0][n] / per[base][0][n] for n in names]
        random.seed(1)
        bs = sorted(gmean([random.choice(ratios) for _ in ratios]) for _ in range(4000))
        print(f"{arm} vs {base}: t/s {100 * (gmean(ratios) - 1):+.2f}% [{100 * (bs[100] - 1):+.2f}, {100 * (bs[3899] - 1):+.2f}] "
              f"over {len(names)} prompts; " + ", ".join(f"{n} {100 * (r - 1):+.1f}%" for n, r in zip(names, ratios)))


if __name__ == "__main__":
    main()
