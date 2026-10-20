#!/usr/bin/env python3
"""Dynamic (EAGLE-2-like) tree ceiling on the server's greedy MTP chain + leaf siblings, priced per step (CPU only).

Input: tree_extract.py --greedy output (the chain fed its own argmax, top-40 per depth) + phase-1 teacher data.
Per start: chain nodes c_1..c_D and leaf siblings (rank rho >= 1 of the chain logits at depth k). The drafter's own
estimate of a node is the product of MTP probabilities along its path; a node is accepted with probability
  on_k * p'_k(token),  on_k = prod_{i<k} 1[x_i == c_i] w_i  (realized prefix; expected value at the last level).
Policies:
  fixed-n : the n nodes with the highest drafter estimate (always a valid tree: estimates fall along every path);
  chain4+sib(tau): chain-4 always, plus every leaf sibling with estimate >= tau (rows capped at --max-rows).
Cost: ms(rows) = BASE + SLOPE * (rows - 5) up to 8 rows; the 9th row costs CLIFF, later rows LATE each.
Draft passes = max depth (4 = production); a 5th depth adds one MTP pass (PASS ms).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

MT = Path.home() / "qwen-opt/mtp-train"
sys.path.insert(0, str(MT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze import load, read_seqs_bin  # noqa: E402
from tree_ceiling import THINK_END, prob_of, sampler  # noqa: E402

M = 4
K = 5


def ms_of(rows, depth, a):
    extra = np.maximum(rows - 5, 0)
    lin = np.minimum(extra, 3) * a.slope
    cl = np.where(rows >= 9, a.cliff, 0.0)
    late = np.maximum(rows - 9, 0) * a.late
    return a.base + lin + cl + late + np.maximum(depth - 4, 0) * a.pass_ms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ext", default=str(Path.home() / "qwen-opt/tree/ext_greedy"))
    ap.add_argument("--T", type=float, default=1.0)
    ap.add_argument("--top-k", type=int, default=20)
    ap.add_argument("--base", type=float, default=27.6)
    ap.add_argument("--slope", type=float, default=0.85)
    ap.add_argument("--cliff", type=float, default=1.37)
    ap.add_argument("--late", type=float, default=0.6)
    ap.add_argument("--pass-ms", type=float, default=0.85)
    ap.add_argument("--max-rows", type=int, default=8)
    a = ap.parse_args()
    hd, seqs = load(MT / "data/ext_p1", MT / "data/p1.idx.jsonl")
    toks = read_seqs_bin(str(MT / "data/p1.bin"))
    groups = {}
    for f in sorted(Path(a.ext).glob("*.npz")):
        si = int(f.stem)
        s = seqs[si]
        z = np.load(f)
        T_, npr = int(z["n_tok"]), int(z["n_prompt"])
        tokens = toks[si]
        J = T_ - npr - K + 1
        if J <= 0:
            continue
        ids_T, p_T = sampler(s["top_id"], s["top_lp"], a.T, a.top_k, 0.95, 0.05)
        ids1, p1 = sampler(s["top_id"], s["top_lp"], 1.0, 20, 0.95, 0.05)
        j = np.arange(J)
        est = np.zeros((J, K, M))      # drafter estimate of node (depth k, rank rho) under the greedy chain
        val = np.zeros((J, K, M))      # acceptance probability of that node
        on = np.ones(J)
        cum = np.ones(J)
        for k in range(1, K + 1):
            row = j + k - 1
            x = tokens[npr - 1 + j + k]
            q = np.exp(z["top_lp"][k - 1, :J, :M].astype(np.float64))
            cand = z["top_id"][k - 1, :J, :M]
            est[:, k - 1] = cum[:, None] * q
            val[:, k - 1] = on[:, None] * prob_of(ids_T[row][:, None, :], p_T[row][:, None, :], cand)
            pT = prob_of(ids_T[row], p_T[row], x)
            p1x = prob_of(ids1[row], p1[row], x)
            w = np.where(p1x > 0, pT / np.maximum(p1x, 1e-300), 0.0)
            on = on * (cand[:, 0] == x) * w
            cum = cum * q[:, 0]
        m = s["meta"]
        cat = f"{m['lang']}-{m['cat']}"
        te = np.flatnonzero(tokens == THINK_END)
        is_think = (npr + j) <= (te[0] if len(te) else len(tokens))
        for g, msk in ((cat, np.ones(J, bool)), (f"{cat}/answer", ~is_think),
                       ("prose", np.ones(J, bool) if m["cat"] == "prose" else np.zeros(J, bool))):
            if msk.any():
                groups.setdefault(g, []).append((est[msk], val[msk]))
    res = {}
    for g, lst in sorted(groups.items()):
        est = np.concatenate([e for e, _ in lst])
        val = np.concatenate([v for _, v in lst])
        n = len(est)
        base_tok = 1 + val[:, :4, 0].sum(1).mean()
        base_ms = a.base
        r = {"n": n, "chain4_tok": round(float(base_tok), 4), "policies": []}
        # chain4 + siblings above tau (siblings at depths 1..4)
        sib_e = est[:, :4, 1:].reshape(n, -1)
        sib_v = val[:, :4, 1:].reshape(n, -1)
        order = np.argsort(-sib_e, 1)
        se = np.take_along_axis(sib_e, order, 1)
        sv = np.take_along_axis(sib_v, order, 1)
        cap = a.max_rows - 5
        for tau in (0.02, 0.05, 0.08, 0.1, 0.15, 0.2, 0.3):
            take = (se >= tau) & (np.arange(se.shape[1])[None, :] < cap)
            rows = 5 + take.sum(1)
            tok = 1 + val[:, :4, 0].sum(1) + (sv * take).sum(1)
            ms = ms_of(rows, 4, a)
            gain = tok.mean() / ms.mean() / (base_tok / base_ms) - 1
            r["policies"].append({"policy": f"chain4+sib tau={tau}", "rows": round(float(rows.mean()), 3),
                                  "tok": round(float(tok.mean()), 4), "ms": round(float(ms.mean()), 3),
                                  "dtok%": round(100 * (tok.mean() / base_tok - 1), 2), "net%": round(100 * gain, 2)})
        # fixed-n best-first by drafter estimate over chain(depth<=Dmax) + siblings
        for Dmax in (4, 5):
            e = est[:, :Dmax].reshape(n, -1)
            v = val[:, :Dmax].reshape(n, -1)
            dep = np.repeat(np.arange(1, Dmax + 1), M)[None, :].repeat(n, 0)
            o = np.argsort(-e, 1)
            vv = np.take_along_axis(v, o, 1)
            dd = np.take_along_axis(dep, o, 1)
            for nn in range(3, 9):
                tok = 1 + vv[:, :nn].sum(1)
                depth = dd[:, :nn].max(1)
                rows = np.full(n, 1 + nn)
                ms = ms_of(rows, depth, a)
                gain = tok.mean() / ms.mean() / (base_tok / base_ms) - 1
                r["policies"].append({"policy": f"best-first n={nn} Dmax={Dmax}", "rows": 1 + nn,
                                      "depth": round(float(depth.mean()), 3), "tok": round(float(tok.mean()), 4),
                                      "ms": round(float(ms.mean()), 3),
                                      "dtok%": round(100 * (tok.mean() / base_tok - 1), 2),
                                      "net%": round(100 * gain, 2)})
        res[g] = r
        print(f"== {g} n={n} chain4 tok/step {r['chain4_tok']}")
        for p in r["policies"]:
            print(f"   {p['policy']:<28} rows {p['rows']:<6} tok {p['tok']:<7} ms {p['ms']:<7} "
                  f"dtok {p['dtok%']:+.2f}%  net {p['net%']:+.2f}%")
    print(json.dumps({"T": a.T, "cost": vars(a)}, default=str))


if __name__ == "__main__":
    main()
