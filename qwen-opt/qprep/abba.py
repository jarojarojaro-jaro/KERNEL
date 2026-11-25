#!/usr/bin/env python3
"""ABBA summary for the K-018/K-019/K-038 arms: rows of copy_bench.jsonl / spec_sweep.jsonl / sealed.jsonl in DIR whose
label starts with an arm label (A1/A2 vs B1/B2 or any two label groups). Per (file, set, temperature): mean of the arm
medians A vs B and the delta; per prompt t/s, tok/step and ms/step deltas; T=0 md5 per prompt equal or not.

usage: abba.py DIR --a k018-A1,k018-A2 --b k018-B1,k018-B2
"""
import argparse, json, os, statistics
from collections import defaultdict


def arm_of(label, groups):
    for g, labels in groups.items():
        for l in labels:
            if label == l or label.startswith(l + "-"):
                return g
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    a = ap.parse_args()
    groups = {"A": a.a.split(","), "B": a.b.split(",")}
    for fn in ("copy_bench.jsonl", "spec_sweep.jsonl", "sealed.jsonl"):
        p = os.path.join(a.dir, fn)
        if not os.path.exists(p):
            continue
        cell = defaultdict(lambda: {"A": [], "B": []})
        for line in open(p):
            r = json.loads(line)
            g = arm_of(r["label"], groups)
            if g:
                cell[(r.get("set", "-"), r["temp"])][g].append(r)
        for (st, temp), arms in sorted(cell.items()):
            if not arms["A"] or not arms["B"]:
                continue
            ma = statistics.mean(r["median_tps"] for r in arms["A"])
            mb = statistics.mean(r["median_tps"] for r in arms["B"])
            print(f"{fn} set={st} T={temp}: A {ma:7.2f}  B {mb:7.2f}  {100 * (mb / ma - 1):+6.2f}%  "
                  f"(n {len(arms['A'])}/{len(arms['B'])})")
            names = arms["A"][0]["prompts"].keys()
            for n in names:
                def m(g, k):
                    v = [r["prompts"][n][k] for r in arms[g] if n in r["prompts"] and k in r["prompts"][n]]
                    return statistics.mean(v) if v else float("nan")
                line = (f"    {n:24s} t/s {m('A', 'tps'):7.2f} -> {m('B', 'tps'):7.2f} ({100 * (m('B', 'tps') / m('A', 'tps') - 1):+6.2f}%)"
                        f"  tok/step {m('A', 'tok_step'):.3f} -> {m('B', 'tok_step'):.3f}")
                if "ms_step" in arms["A"][0]["prompts"][n]:
                    line += f"  ms/step {m('A', 'ms_step'):.2f} -> {m('B', 'ms_step'):.2f}"
                if temp == 0.0 and "md5" in arms["A"][0]["prompts"][n]:
                    md = {g: {tuple(r["prompts"][n]["md5"]) for r in arms[g]} for g in "AB"}
                    line += "  md5 " + ("=" if md["A"] == md["B"] and len(md["A"]) == 1 else f"DIFF {md}")
                print(line)


if __name__ == "__main__":
    main()
