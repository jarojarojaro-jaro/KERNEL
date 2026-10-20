#!/usr/bin/env python3
"""E0 summaries (report 37) of prose_bench.py rows (and copy_bench.py mvs rows).

ARM = label without PREFIX and without a trailing repeat letter a-d (p37-h0a, p37-h0b -> h0).
Per arm: t/s = sum tokens / sum time, tok/step, ms/step (step = n - accepted), 95% bootstrap CI over prompts
(prompt = unit, all its seeds and repeats together). Versus BASE: the same totals restricted to the (prompt, seed)
cells both arms have, ratio with a paired bootstrap CI over prompts, and how many cells have identical text (md5).

usage: prose_sum.py FILE PREFIX BASE [--mvs copy_bench.jsonl]
"""
import argparse
import collections
import json
import math
import random
import re
import statistics


def arm_of(label, prefix):
    return re.sub(r"(?<=[0-9A-Za-z])[a-d]$", "", label[len(prefix):])


def totals(cells, keys):
    n = sum(c["n"] for k in keys for c in cells[k])
    ms = sum(c["ms"] for k in keys for c in cells[k])
    st = sum(c["n"] - c["accepted"] for k in keys for c in cells[k])
    return n, ms, st


def boot(prompts, f, reps=4000):
    random.seed(1)
    v = sorted(f([random.choice(prompts) for _ in prompts]) for _ in range(reps))
    return v[int(0.025 * reps)], v[int(0.975 * reps) - 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("prefix")
    ap.add_argument("base")
    ap.add_argument("--mvs", default=None)
    a = ap.parse_args()
    cells = collections.defaultdict(list)          # (arm, prompt, seed) -> rows
    for line in open(a.file):
        if not line.strip():
            continue
        r = json.loads(line)
        if r["label"].startswith(a.prefix):
            cells[(arm_of(r["label"], a.prefix), r["prompt"], r["seed"])].append(r)
    arms = sorted({k[0] for k in cells}, key=lambda x: (x != a.base, x))
    labels = collections.defaultdict(list)
    for line in open(a.file):
        r = json.loads(line) if line.strip() else None
        if r and r["label"].startswith(a.prefix):
            labels[r["label"]].append(r)
    for arm in arms:
        ks = [k for k in cells if k[0] == arm]
        prompts = sorted({k[1] for k in ks})
        n, ms, st = totals(cells, ks)
        tps = 1000 * n / ms

        def f(ps, arm=arm):
            kk = [k for p in ps for k in ks if k[1] == p]
            nn, mm, _ = totals(cells, kk)
            return 1000 * nn / mm
        lo, hi = boot(prompts, f)
        reps = collections.Counter(len(cells[k]) for k in ks)
        print(f"{arm:10} {tps:7.2f} t/s [{lo:.2f}, {hi:.2f}] ({100 * (lo / tps - 1):+.1f}/{100 * (hi / tps - 1):+.1f}%)  "
              f"tok/step {n / st:.3f}  ms/step {ms / st:.3f}  tokens {n}  cells {len(ks)} reps {dict(reps)}")
        per = []
        for p in prompts:
            pn, pm, ps_ = totals(cells, [k for k in ks if k[1] == p])
            per.append(f"{p} {1000 * pn / pm:.1f}")
        print("           " + "  ".join(per))
    base_keys = {k[1:] for k in cells if k[0] == a.base}
    for arm in arms:
        if arm == a.base:
            continue
        common = sorted({k[1:] for k in cells if k[0] == arm} & base_keys)
        if not common:
            continue
        prompts = sorted({c[0] for c in common})

        def ratio(ps, key):
            kk = [c for p in ps for c in common if c[0] == p]
            na, ma, sa = totals(cells, [(arm,) + c for c in kk])
            nb, mb, sb = totals(cells, [(a.base,) + c for c in kk])
            return {"tps": (na / ma) / (nb / mb), "ms_step": (ma / sa) / (mb / sb), "tok_step": (na / sa) / (nb / sb)}[key]
        same = sum(1 for c in common if {r["md5"] for r in cells[(arm,) + c]} == {r["md5"] for r in cells[(a.base,) + c]}
                   and len({r["md5"] for r in cells[(arm,) + c]}) == 1)
        out = f"{arm} vs {a.base} ({len(common)} cells):"
        for key in ("tps", "ms_step", "tok_step"):
            g = ratio(prompts, key)
            lo, hi = boot(prompts, lambda ps, key=key: ratio(ps, key))
            out += f"  {key} {100 * (g - 1):+.2f}% [{100 * (lo - 1):+.2f}, {100 * (hi - 1):+.2f}]"
        print(out + f"  identical text {same}/{len(common)}")
    # every server instance (label) on its own vs the base arm on the same cells: the ABBA spread (A/A = noise floor)
    base_cells = [k for k in cells if k[0] == a.base]
    if base_cells:
        bn, bm, bs = totals(cells, base_cells)
        out = []
        for lab in sorted(labels):
            rr = labels[lab]
            n = sum(r["n"] for r in rr); ms = sum(r["ms"] for r in rr); st = sum(r["n"] - r["accepted"] for r in rr)
            kk = {(a.base, r["prompt"], r["seed"]) for r in rr} & set(base_cells)
            if len(kk) == len(rr):
                kn, km, ks_ = totals(cells, kk)
                out.append(f"{lab[len(a.prefix):]} {ms / st:.3f} ({100 * ((ms / st) / (km / ks_) - 1):+.2f}%)")
        print(f"ms/step per instance vs {a.base} mean on the same cells: " + "  ".join(out))
    if a.mvs:
        mv = collections.defaultdict(list)          # arm -> rows (one row = one run over the mvs files, T=0)
        for l in open(a.mvs):
            r = json.loads(l) if l.strip() else None
            if r and r["label"].startswith(a.prefix):
                mv[arm_of(r["label"], a.prefix)].append(r)

        def gm(rows, key):
            files = sorted(rows[0]["prompts"])
            return math.exp(statistics.mean(math.log(statistics.mean(r["prompts"][f][key] for r in rows)) for f in files))
        for arm in arms:
            if not mv.get(arm):
                continue
            md5 = {f: {",".join(r["prompts"][f]["md5"]) for r in mv[arm]} for f in mv[arm][0]["prompts"]}
            out = (f"mvs {arm:8} geomean t/s {gm(mv[arm], 'tps'):.1f}  ms/step {gm(mv[arm], 'ms_step'):.2f}  "
                   f"runs {len(mv[arm])}")
            if arm != a.base and mv.get(a.base):
                bmd5 = {f: {",".join(r["prompts"][f]["md5"]) for r in mv[a.base]} for f in md5}
                out += (f"  vs {a.base}: t/s {100 * (gm(mv[arm], 'tps') / gm(mv[a.base], 'tps') - 1):+.2f}%"
                        f"  ms/step {100 * (gm(mv[arm], 'ms_step') / gm(mv[a.base], 'ms_step') - 1):+.2f}%"
                        f"  md5 same {sum(md5[f] == bmd5[f] and len(md5[f]) == 1 for f in md5)}/{len(md5)}")
            print(out)


if __name__ == "__main__":
    main()
