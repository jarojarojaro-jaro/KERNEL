#!/usr/bin/env python3
"""Report 40: per-position draft acceptance on the E0 prose set from the production server's per-step log
(LLAMA_SPEC_LOOKUP_LOG, one line per speculative step: drafts d, MTP drafts nd, kind k 0=MTP 1=MTP+lookup tail
2=lookup chain, accepted a; id = the token sampled at the end of the previous step).

Requests in log order = warmup + pa_bench.py rows in file order (label LABEL). The token the target sampled where the
chain broke is the next step's id. Outputs a JSON summary and prints the tables used in the report.
usage: pa_analyze.py LABEL [--logdir DIR]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tokclass  # noqa: E402

NV = 248320


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("label")
    ap.add_argument("--logdir", default=str(HERE / "logs"))
    a = ap.parse_args()
    ld = Path(a.logdir)
    rows = [json.loads(l) for l in open(ld / "pa.jsonl")]
    rows = [r for r in rows if r["label"] == a.label]
    steps = defaultdict(list)
    begins = []
    for l in open(ld / f"{a.label}.lk.jsonl"):
        o = json.loads(l)
        if "b" in o:
            begins.append(o["b"])
        else:
            steps[o["r"]].append(o)
    reqs = sorted(begins)
    assert len(reqs) == len(rows) + 1, (len(reqs), len(rows))
    cls, strs = tokclass.classes(NV)
    C = tokclass.CLASSES
    res = {}
    groups = defaultdict(list)
    for rq, row in zip(reqs[1:], rows):
        g = f"T{row['temp']:g}"
        lang = row["prompt"][:2]
        st = steps.get(rq, [])
        groups[g].append((row, st))
        groups[f"{g}/{lang}"].append((row, st))
        groups[f"{g}/{row['prompt']}"].append((row, st))
    for g, lst in groups.items():
        nmax = 4
        alive = np.zeros(nmax + 1)
        acc = np.zeros(nmax + 1)
        n_steps = n_tok_gen = 0
        kinds = Counter()
        kind_acc = Counter()
        brk_x = Counter()
        brk_pair = Counter()
        brk_depth = Counter()
        gen_cls = Counter()
        brk_same_stem = 0
        brk_examples = Counter()
        for row, st in lst:
            n_tok_gen += row["n"]
            for i, s in enumerate(st):
                n_steps += 1
                d, nd, k, na = s["d"], s["nd"], s["k"], s["a"]
                kinds[k] += 1
                kind_acc[k] += na
                # generated tokens of this step: accepted drafts + the next id
                nxt = st[i + 1]["id"] if i + 1 < len(st) else None
                for t in d[:na]:
                    gen_cls[C[cls[t]]] += 1
                if nxt is not None:
                    gen_cls[C[cls[nxt]]] += 1
                if k == 2:      # lookup-only chain: not a draft position of the MTP head
                    continue
                m = min(nd, nmax)
                for j in range(1, m + 1):
                    if na >= j - 1:
                        alive[j] += 1
                        if na >= j:
                            acc[j] += 1
                if na < m and nxt is not None:   # the chain broke at depth na+1 on an MTP draft
                    x, dt = nxt, d[na]
                    cx, cd = C[cls[x]], C[cls[dt]]
                    brk_x[cx] += 1
                    brk_pair[(cx, cd)] += 1
                    brk_depth[na + 1] += 1
                    sx, sd = strs[x].strip().lower(), strs[dt].strip().lower()
                    if cx == "cont" and cd == "cont" or (cx == "wstart" and cd == "wstart" and len(sx) >= 3
                                                         and len(sd) >= 3 and sx[:3] == sd[:3]):
                        brk_same_stem += 1
                    if g == "T1/pl":
                        brk_examples[(strs[dt], strs[x])] += 1
        S = [acc[j] / max(1, n_steps) for j in range(1, nmax + 1)]
        cond = [acc[j] / max(1, alive[j]) for j in range(1, nmax + 1)]
        nb = sum(brk_x.values())
        ng = sum(gen_cls.values())
        r = {"requests": len(lst), "tokens": n_tok_gen, "steps": n_steps,
             "tok_per_step": round(n_tok_gen / max(1, n_steps), 4),
             "tok_per_step_model": round(1 + sum(S), 4),
             "S": [round(x, 4) for x in S], "cond": [round(x, 4) for x in cond],
             "alive": [int(x) for x in alive[1:]],
             "kinds": dict(kinds), "kind_accepted": dict(kind_acc),
             "t_s": round(1000 * sum(rw["n"] for rw, _ in lst) / sum(rw["ms"] for rw, _ in lst), 2),
             "ms_step": round(sum(rw["ms"] for rw, _ in lst) / max(1, n_steps), 3),
             "break_class": {c: round(brk_x[c] / max(1, nb), 4) for c in C},
             "break_depth": {int(k): round(v / max(1, nb), 4) for k, v in sorted(brk_depth.items())},
             "break_same_stem_or_ending": round(brk_same_stem / max(1, nb), 4),
             "break_pairs_top": [[f"{a_}<-{b_}", round(v / max(1, nb), 4)] for (a_, b_), v in brk_pair.most_common(8)],
             "gen_class": {c: round(gen_cls[c] / max(1, ng), 4) for c in C}}
        if brk_examples:
            r["examples_draft_vs_target"] = [[d_, x_, v] for (d_, x_), v in brk_examples.most_common(30)]
        res[g] = r
    out = ld / f"{a.label}.summary.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    for g in sorted(res):
        r = res[g]
        if g.count("/") == 1 and len(g.split("/")[1]) > 2:
            print(f"{g:22s} t/s {r['t_s']:6.2f} tok/step {r['tok_per_step']:.3f} cond {r['cond']}")
            continue
        print(f"== {g}: req {r['requests']} tok {r['tokens']} steps {r['steps']} t/s {r['t_s']} ms/step {r['ms_step']}"
              f" tok/step {r['tok_per_step']} (1+sum S {r['tok_per_step_model']})")
        print(f"   S {r['S']} cond {r['cond']} kinds {r['kinds']} kind_acc {r['kind_accepted']}")
        print(f"   break class {r['break_class']} depth {r['break_depth']} same-stem {r['break_same_stem_or_ending']}")
        print(f"   pairs {r['break_pairs_top']}")
        print(f"   generated {r['gen_class']}")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
