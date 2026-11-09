#!/usr/bin/env python3
"""R68b: offline sim of a Gumbo-style dynamic tree on the COUPLED MTP chain (CPU only).

Reuses the 24s data and estimators (tree_ceiling.py). For every start and depth k=1..5 on the realized path it draws S
posterior Gumbel noises given the target's sampled token x (coupled_rank logic) and records per sample:
  r = rank of x among the draft's perturbed scores (log q~ + G), gap = s(1st) - s(2nd) of the perturbed draft scores.
Policy (decided at draft time, before verification): chain-4 + a sibling leaf (2nd perturbed candidate) at depth k
whenever gap_k < tau. Depths are independent given the realized path (fresh noise per position), so
  tok/step = 1 + sum_k prod_{j<k} P(r_j=0) * [P(r_k=0) + P(r_k=1, gap_k<tau)]   (chain node k or its sibling)
  ... where chain value continues only through r_k = 0.
Rows = 5 + sum_k P(gap_k < tau). Cost model as in 24s: 27.6 ms at 5 rows, +0.85 ms/row to 8, 9th row +1.37 ms.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path.home() / "KERNEL/product/research/24s-drzewa"))
import tree_ceiling as tc  # noqa: E402

K, M = 5, tc.M
TAUS = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 1e9]


def rank_gap(t_ids, t_p, d_ids, d_ls, x, rng, S):
    """Same posterior noise model as tc.coupled_rank_dist; returns rank [n,S] (M = miss) and gap [n,S]."""
    n = len(x)
    R = np.full((n, S), M, np.int64)
    GAP = np.zeros((n, S))
    lpt = np.where(t_p > 0, np.log(np.maximum(t_p, 1e-300)), -np.inf)
    in_t = d_ids[:, :, None] == t_ids[:, None, :]
    t_idx = np.where(in_t.any(-1), in_t.argmax(-1), -1)
    x_slot_t = (t_ids == x[:, None]).argmax(-1)
    x_in_t = (t_ids == x[:, None]).any(-1) & (t_p[np.arange(n), x_slot_t] > 0)
    x_in_d = (d_ids == x[:, None]) & np.isfinite(d_ls)
    x_slot_d = x_in_d.argmax(-1)
    has_xd = x_in_d.any(-1)
    for c0 in range(0, n, 1024):
        sl = slice(c0, min(n, c0 + 1024))
        m = sl.stop - sl.start
        Mx = tc.gumbel((m, S, 1), rng)
        loc = lpt[sl][:, None, :]
        Fm = np.exp(-np.exp(-(Mx - loc)))
        u = rng.random((m, S, lpt.shape[1])) * Fm
        y = loc - np.log(-np.log(np.maximum(u, 1e-300)))
        Gt = y - loc
        xs = x_slot_t[sl]
        Gt[np.arange(m), :, xs] = (Mx[:, :, 0] - lpt[sl][np.arange(m), xs][:, None])
        Gd = tc.gumbel((m, S, d_ids.shape[1]), rng)
        ti = t_idx[sl]
        use_t = (ti >= 0) & np.isfinite(lpt[sl][np.arange(m)[:, None], np.maximum(ti, 0)])
        Gd = np.where(use_t[:, None, :], np.take_along_axis(Gt, np.maximum(ti, 0)[:, None, :].repeat(S, 1), 2), Gd)
        sc = d_ls[sl][:, None, :] + Gd
        sc = np.where(np.isfinite(sc), sc, -np.inf)
        top2 = -np.sort(-sc, axis=-1)[:, :, :2]
        GAP[sl] = np.where(np.isfinite(top2[:, :, 1]), top2[:, :, 0] - top2[:, :, 1], 1e9)
        xd = x_slot_d[sl]
        sx = sc[np.arange(m), :, xd]
        rk = (sc > sx[:, :, None]).sum(-1)
        rk = np.where((has_xd[sl] & x_in_t[sl])[:, None], rk, M)
        R[sl] = np.minimum(rk, M)
    return R, GAP


def cost(rows):
    import os
    rc = float(os.environ.get("ROWC", "0.85"))
    extra = np.clip(rows - 5, 0, 3) * rc + np.clip(rows - 8, 0, None) * (rc + 0.52)
    return 27.6 + extra


def main():
    S = int(sys.argv[1]) if len(sys.argv) > 1 else 64
    rng = np.random.default_rng(68)
    hd, seqs = tc.load(tc.MT / "data/ext_p1", tc.MT / "data/p1.idx.jsonl")
    toks = tc.read_seqs_bin(str(tc.MT / "data/p1.bin"))
    acc = defaultdict(lambda: defaultdict(list))
    for f in sorted((Path.home() / "qwen-opt/tree/ext").glob("*.npz")):
        si = int(f.stem)
        s = seqs[si]
        z = np.load(f)
        T_, npr = int(z["n_tok"]), int(z["n_prompt"])
        tokens = toks[si]
        J = T_ - npr - K + 1
        if J <= 0:
            continue
        ids_all, p_all = tc.sampler(s["top_id"], s["top_lp"], 1.0, 20, 0.95, 0.05)
        j = np.arange(J)
        per = {}
        for k in range(1, K + 1):
            row = j + k - 1
            x = tokens[npr - 1 + j + k]
            dls = tc.draft_filtered(z["top_lp"][k - 1, :J], 20, 0.95, 0.05, 1.0)
            R, GAP = rank_gap(ids_all[row], p_all[row], z["top_id"][k - 1, :J], dls, x, rng, S)
            per[f"p0_{k}"] = (R == 0).mean(1)
            for t in TAUS:
                g = GAP < t
                per[f"sib_{k}_{t}"] = ((R == 1) & g).mean(1)
                per[f"use_{k}_{t}"] = g.mean(1)
        m = s["meta"]
        cat = f"{m['lang']}-{m['cat']}"
        for gname, msk in ((cat, np.ones(J, bool)), ("all", np.ones(J, bool)),
                           ("prose", np.ones(J, bool) if m["cat"] == "prose" else np.zeros(J, bool))):
            if msk.any():
                for kk, v in per.items():
                    acc[gname][kk].append(v[msk])
    for g in sorted(acc):
        d = {kk: np.concatenate(v) for kk, v in acc[g].items()}
        n = len(d["p0_1"])
        # chain-4 baseline (coupled) and chain-5
        A = np.ones(n)
        chain = [1.0]
        for k in range(1, K + 1):
            A = A * d[f"p0_{k}"]
            chain.append(chain[-1] + float(A.mean()))
        base_tok, base_ms = chain[4], cost(5)
        print(f"== {g} n={n} coupled chain-4 tok/step {base_tok:.4f} (chain-5 {chain[5]:.4f}, "
              f"net {((chain[5] / cost(6)) / (base_tok / base_ms) - 1) * 100:+.2f}%)")
        for t in TAUS:
            A = np.ones(n)
            tok, rows = 1.0, 5.0
            for k in range(1, 5):
                tok += float((A * (d[f"p0_{k}"] + d[f"sib_{k}_{t}"])).mean())
                rows += float(d[f"use_{k}_{t}"].mean())
                A = A * d[f"p0_{k}"]
            ms = float(cost(rows))
            net = (tok / ms) / (base_tok / base_ms) - 1
            print(f"   chain4 + Gumbel-gap sibling tau={t:<6} rows {rows:6.3f} tok {tok:.4f} "
                  f"dtok {(tok / base_tok - 1) * 100:+6.2f}%  ms {ms:6.2f}  net {net * 100:+6.2f}%")
        # per-row sensitivity at the best tau for a cheaper row (0.57 ms, 24s threshold)
    return 0


if __name__ == "__main__":
    main()
