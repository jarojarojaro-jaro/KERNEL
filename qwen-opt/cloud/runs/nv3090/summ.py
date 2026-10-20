#!/usr/bin/env python3
"""ABBA summary of sweep.py rows (nv-3090, 2026-10-20).

usage: summ.py rows.jsonl [--pairs A:B,...] [--labels prefix]
Per label and set: pooled t/s (sum n / sum ms), ms/step (sum ms / sum(n - accepted)), tok/step.
Arms are labels with the pass suffix stripped ('.p1', '.p2', ...): pooled over passes, with per-pass values.
--pairs A:B: B vs A paired over (set, prompt, temp, seed) present in both, bootstrap 95% CI of the ratio of pooled
t/s and of pooled ms/step (2000 resamples over request keys).
"""
import argparse
import collections
import json
import random
import re


def load(path):
    rows = [json.loads(line) for line in open(path)]
    for r in rows:
        r["arm"] = re.sub(r"\.p\d+$", "", r["label"])
    return rows


def pooled(rs):
    n = sum(r["n"] for r in rs); ms = sum(r["ms"] for r in rs); ac = sum(r["accepted"] for r in rs)
    st = max(1, n - ac)
    return 1000 * n / ms, ms / st, n / st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rows")
    ap.add_argument("--pairs", default="")
    ap.add_argument("--labels", default="")
    a = ap.parse_args()
    rows = [r for r in load(a.rows) if r["label"].startswith(a.labels)]
    by = collections.defaultdict(list)
    for r in rows:
        by[(r["arm"], r["set"], r["temp"])].append(r)
    print(f"{'arm':28s} {'set':6s} {'T':>4s} {'t/s':>7s} {'ms/st':>7s} {'tok/st':>6s}  passes")
    for (arm, s, t), rs in sorted(by.items()):
        tps, mss, tks = pooled(rs)
        passes = collections.defaultdict(list)
        for r in rs:
            passes[r["label"]].append(r)
        pp = " ".join(f"{l.rsplit('.', 1)[-1]}={pooled(v)[0]:.1f}" for l, v in sorted(passes.items()))
        print(f"{arm:28s} {s:6s} {t:4.1f} {tps:7.2f} {mss:7.2f} {tks:6.2f}  {pp}")
    for pr in filter(None, a.pairs.split(",")):
        A, B = pr.split(":")
        for s in sorted({r["set"] for r in rows}):
            for t in sorted({r["temp"] for r in rows}):
                ka = collections.defaultdict(list); kb = collections.defaultdict(list)
                for r in rows:
                    if r["set"] != s or r["temp"] != t:
                        continue
                    k = (r["prompt"], r["seed"])
                    if r["arm"] == A:
                        ka[k].append(r)
                    elif r["arm"] == B:
                        kb[k].append(r)
                keys = sorted(set(ka) & set(kb))
                if not keys:
                    continue
                def ratio(ks):
                    ra = [x for k in ks for x in ka[k]]; rb = [x for k in ks for x in kb[k]]
                    pa, pb = pooled(ra), pooled(rb)
                    return pb[0] / pa[0] - 1, pb[1] / pa[1] - 1
                base = ratio(keys)
                rnd = random.Random(1)
                bs = sorted(ratio([rnd.choice(keys) for _ in keys]) for _ in range(2000))
                tl = sorted(x[0] for x in bs); ml = sorted(x[1] for x in bs)
                print(f"{B} vs {A} [{s} T={t}, {len(keys)} keys]: t/s {100*base[0]:+.2f}% "
                      f"[{100*tl[50]:+.2f}, {100*tl[1949]:+.2f}]  ms/step {100*base[1]:+.2f}% "
                      f"[{100*ml[50]:+.2f}, {100*ml[1949]:+.2f}]")


if __name__ == "__main__":
    main()
