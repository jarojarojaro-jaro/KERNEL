#!/usr/bin/env python3
"""ABBA statistics for ab.sh runs: B vs A per prompt (chat T=1 spec_sweep, mvs T=0 copy_bench).
Pairs each prompt's A and B means over the passes; reports mean t/s, ms/step, tok/step and the B/A change of t/s with a
bootstrap 95% CI over prompts (10k resamples, seed 0).
usage: ab_stats.py LOGDIR NAME
"""
import json
import random
import statistics
import sys


def load(path, name):
    out = {}
    for line in open(path):
        d = json.loads(line)
        lab = d["label"]
        if not lab.startswith(f"ab.{name}."):
            continue
        if "set" in d and d["set"] != "mvs":
            continue
        arm = lab.split(".")[2]
        for p, r in d["prompts"].items():
            out.setdefault(arm, {}).setdefault(p, []).append(r)
    return out


def summar(tag, data):
    if "A" not in data or "B" not in data:
        print(f"{tag}: missing arm"); return
    prompts = sorted(set(data["A"]) & set(data["B"]))
    rat = []
    for p in prompts:
        a = statistics.mean(r["tps"] for r in data["A"][p]); b = statistics.mean(r["tps"] for r in data["B"][p])
        rat.append(b / a - 1)
    def m(arm, k):
        return statistics.mean(statistics.mean(r[k] for r in data[arm][p]) for p in prompts)
    rng = random.Random(0)
    boots = sorted(statistics.mean(rng.choice(rat) for _ in rat) for _ in range(10000))
    lo, hi = boots[250], boots[9749]
    print(f"{tag}: A {m('A','tps'):.2f} t/s {m('A','ms_step'):.2f} ms/step {m('A','tok_step'):.3f} tok/step | "
          f"B {m('B','tps'):.2f} t/s {m('B','ms_step'):.2f} ms/step {m('B','tok_step'):.3f} tok/step | "
          f"B/A t/s {100*statistics.mean(rat):+.2f}% CI95 [{100*lo:+.2f}, {100*hi:+.2f}] "
          f"ms/step {100*(m('B','ms_step')/m('A','ms_step')-1):+.2f}% (n={len(prompts)} prompts, passes "
          f"A={len(data['A'][prompts[0]])} B={len(data['B'][prompts[0]])})")


if __name__ == "__main__":
    d, name = sys.argv[1], sys.argv[2]
    summar("chat T=1", load(f"{d}/spec_sweep.jsonl", name))
    summar("mvs T=0", load(f"{d}/copy_bench.jsonl", name))
