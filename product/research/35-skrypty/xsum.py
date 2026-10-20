#!/usr/bin/env python3
"""Report-35 summaries. Rows of reason_bench.jsonl / spec_sweep.jsonl / copy_bench.jsonl in LOGDIR whose label
starts with PREFIX; ARM = label with PREFIX and a repeat letter a-d after a digit removed (e1-n4a -> n4, e3-P1 -> P1).
Per arm: per prompt mean t/s, tok/step, ms/step; geometric mean over prompts; vs BASE arm the paired per-prompt
ratio with a bootstrap 95% CI over prompts (prompt = unit; repeats of an arm averaged first).

usage: xsum.py LOGDIR PREFIX BASE [--file reason_bench.jsonl|spec_sweep.jsonl|copy_bench.jsonl]
"""
import argparse
import collections
import json
import math
import pathlib
import random
import re
import statistics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logdir")
    ap.add_argument("prefix")
    ap.add_argument("base")
    ap.add_argument("--file", default="spec_sweep.jsonl")
    a = ap.parse_args()
    rows = [json.loads(l) for l in (pathlib.Path(a.logdir) / a.file).open() if l.strip()]
    cell = collections.defaultdict(list)          # (arm, prompt) -> [dict]
    for r in rows:
        if not r["label"].startswith(a.prefix):
            continue
        arm = re.sub(r"(?<=\d)[a-d]$", "", r["label"][len(a.prefix):])
        for p, v in r["prompts"].items():
            cell[(arm, p)].append(v)
    arms = sorted({k[0] for k in cell})
    prompts = sorted({k[1] for k in cell})
    print(f"{a.file} prefix {a.prefix}: t/s | tok/step | ms/step (mean over repeats, n = repeats)")
    for p in prompts:
        print(f"{p:14} " + " | ".join(
            f"{arm} {statistics.mean(v['tps'] for v in cell[(arm, p)]):6.1f} {statistics.mean(v['tok_step'] for v in cell[(arm, p)]):.2f} "
            f"{statistics.mean(v['ms_step'] for v in cell[(arm, p)]):.2f} n{len(cell[(arm, p)])}" for arm in arms if cell[(arm, p)]))
    for arm in arms:
        ps = [p for p in prompts if cell[(arm, p)] and cell[(a.base, p)]]
        if not ps:
            continue
        gm = lambda key, arm_=arm: math.exp(statistics.mean(math.log(statistics.mean(v[key] for v in cell[(arm_, p)])) for p in ps))
        ratios = {k: [statistics.mean(v[k] for v in cell[(arm, p)]) / statistics.mean(v[k] for v in cell[(a.base, p)]) for p in ps]
                  for k in ("tps", "tok_step", "ms_step")}
        out = f"{arm:6} geomean t/s {gm('tps'):6.1f}  tok/step {gm('tok_step'):.3f}  ms/step {gm('ms_step'):.2f}"
        if arm != a.base:
            random.seed(1)
            for k, r in ratios.items():
                g = math.exp(statistics.mean(map(math.log, r)))
                bs = sorted(math.exp(statistics.mean(math.log(random.choice(r)) for _ in r)) for _ in range(4000))
                out += f" | {k} {100 * (g - 1):+.1f}% [{100 * (bs[100] - 1):+.1f}, {100 * (bs[3899] - 1):+.1f}]"
        print(out)
    md5 = collections.defaultdict(set)
    for (arm, p), vs in cell.items():
        for v in vs:
            if "md5" in v:
                md5[(p, arm)].add(",".join(v["md5"]))
    if md5:
        print("md5 per prompt/arm (one value = deterministic across repeats):")
        for p in prompts:
            print(f"{p:14} " + "  ".join(f"{arm}:{'/'.join(sorted(md5[(p, arm)]))}" for arm in arms if (p, arm) in md5))


if __name__ == "__main__":
    main()
