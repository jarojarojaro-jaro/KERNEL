#!/usr/bin/env python3
"""Offline ceilings for MTP tree / multi-candidate drafting on prose (CPU only, no GPU).

Inputs: tree_extract.py output (MTP logits of every node on the realized path) + the phase-1 teacher data
(~/qwen-opt/mtp-train/data/ext_p1: target top-32 log-probs per response position, sampled tokens).

Verification is sample-and-match (production at T>0, and the coupled sampler of 16k/24p): the target samples one
token per verified row and a tree node is accepted iff its token equals that sample and its parent was accepted.
Any static tree is therefore lossless, and only nodes on the realized path can be accepted. A tree node is a path of
MTP ranks (rho_1..rho_k); its acceptance probability is

  greedy  : v = E[ prod_{i<k} 1[R_i == rho_i] w_i * p'_k(cand rho_k) ]      (R_i = MTP rank of the sampled x_i)
  coupled : v = E[ prod_{i<=k} pi_i(rho_i) w_i ]                              (pi = posterior P(perturbed rank of x))

with w_i = p'_T(x_i) / p'_1(x_i) (importance weight when the evaluated temperature differs from the sampled T=1).
Child values never exceed the parent value, so best-first selection of node values gives the optimal static tree of
every size. tok/step = 1 + sum of node values.
"""
from __future__ import annotations

import argparse
import heapq
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

MT = Path.home() / "qwen-opt/mtp-train"
sys.path.insert(0, str(MT))
from analyze import load, read_seqs_bin  # noqa: E402

THINK_END = 248069
M = 6          # ranks per node considered
K = 5          # depths extracted


def sampler(top_id, top_lp, T, top_k, top_p, min_p):
    """llama.cpp chain top_k -> top_p -> min_p -> temperature on stored top-32 log-probs. Returns ids, probs."""
    lp = top_lp[:, :top_k].astype(np.float64)
    p = np.exp(lp - lp.max(-1, keepdims=True))
    p = p / p.sum(-1, keepdims=True)
    c = np.cumsum(p, -1)
    keep = (c - p) < top_p
    keep &= p >= min_p * p[:, :1]
    keep[:, 0] = True
    pt = np.where(keep, p ** (1.0 / T), 0.0)
    return top_id[:, :top_k], pt / pt.sum(-1, keepdims=True)


def prob_of(ids, probs, tok):
    return (probs * (ids == tok[..., None])).sum(-1)


def draft_filtered(lp, top_k, top_p, min_p, T):
    """Draft-side filter chain of the coupled Gumbel op on MTP log-probs [.., 40] (sorted desc): log q~ (or -inf)."""
    lpk = lp[..., :top_k].astype(np.float64)
    p = np.exp(lpk - lpk[..., :1])
    p = p / p.sum(-1, keepdims=True)
    c = np.cumsum(p, -1)
    keep = (c - p) < top_p
    keep &= p >= min_p * p[..., :1]
    keep[..., 0] = True
    s = np.where(keep, np.log(np.maximum(p, 1e-300)) / T, -np.inf)
    out = np.full(lp.shape, -np.inf)
    out[..., :top_k] = s
    return out


def gumbel(shape, rng):
    return -np.log(-np.log(rng.random(shape)))


def coupled_rank_dist(t_ids, t_p, d_ids, d_ls, x, rng, S):
    """Posterior distribution of the rank of the sampled x among the draft's perturbed scores (log q~ + G), given that
    the target's Gumbel-max sample was x. Rows: positions. t_ids/t_p [n,20] target support; d_ids/d_ls [n,40]
    draft ids and filtered scaled log-probs (-inf outside the draft support). Returns pi [n, M+1] (last = miss)."""
    n = len(x)
    out = np.zeros((n, M + 1))
    lpt = np.where(t_p > 0, np.log(np.maximum(t_p, 1e-300)), -np.inf)          # [n,20]
    # target-side posterior noise for target-support tokens; draft-only tokens get free Gumbels
    in_t = d_ids[:, :, None] == t_ids[:, None, :]                               # [n,40,20]
    t_idx = np.where(in_t.any(-1), in_t.argmax(-1), -1)                         # draft cand -> target slot
    x_slot_t = (t_ids == x[:, None]).argmax(-1)
    x_in_t = (t_ids == x[:, None]).any(-1) & (t_p[np.arange(n), x_slot_t] > 0)
    x_in_d = (d_ids == x[:, None]) & np.isfinite(d_ls)
    x_slot_d = x_in_d.argmax(-1)
    has_xd = x_in_d.any(-1)
    for c0 in range(0, n, 2048):
        sl = slice(c0, min(n, c0 + 2048))
        m = sl.stop - sl.start
        Mx = gumbel((m, S, 1), rng)                                             # max of log p + G (lse = 0)
        loc = lpt[sl][:, None, :]                                               # [m,1,20]
        Fm = np.exp(-np.exp(-(Mx - loc)))                                       # CDF at M
        u = rng.random((m, S, lpt.shape[1])) * Fm
        y = loc - np.log(-np.log(np.maximum(u, 1e-300)))
        Gt = y - loc                                                            # [m,S,20]
        xs = x_slot_t[sl]
        Gt[np.arange(m), :, xs] = (Mx[:, :, 0] - lpt[sl][np.arange(m), xs][:, None])
        Gd = gumbel((m, S, d_ids.shape[1]), rng)                                # free noise
        ti = t_idx[sl]
        use_t = (ti >= 0) & np.isfinite(lpt[sl][np.arange(m)[:, None], np.maximum(ti, 0)])
        Gd = np.where(use_t[:, None, :], np.take_along_axis(Gt, np.maximum(ti, 0)[:, None, :].repeat(S, 1), 2), Gd)
        sc = d_ls[sl][:, None, :] + Gd                                          # [m,S,40]
        xd = x_slot_d[sl]
        sx = sc[np.arange(m), :, xd]                                            # [m,S]
        rk = (sc > sx[:, :, None]).sum(-1)
        rk = np.where((has_xd[sl] & x_in_t[sl])[:, None], rk, M)
        rk = np.minimum(rk, M)
        for r in range(M + 1):
            out[sl, r] = (rk == r).mean(1)
    return out


def best_first(Val, Prop, w_last, n_nodes):
    """Val[k] [N, M] last-level contribution, Prop[k] [N, M] propagation factor. Returns list of (path, value) in
    best-first order (prefix-closed for every prefix of the list)."""
    N = Val[0].shape[0]
    heap = []
    cnt = 0
    one = np.ones(N)
    for r in range(M):
        v = float(Val[0][:, r].mean())
        heapq.heappush(heap, (-v, cnt, (r,), one))
        cnt += 1
    out = []
    while heap and len(out) < n_nodes:
        nv, _, path, A = heapq.heappop(heap)
        out.append((path, -nv))
        k = len(path)
        if k >= len(Val):
            continue
        B = A * Prop[k - 1][:, path[-1]]
        for r in range(M):
            v = float((B * Val[k][:, r]).mean())
            heapq.heappush(heap, (-v, cnt, path + (r,), B))
            cnt += 1
    return out


def chain_value(Val, Prop, n):
    N = Val[0].shape[0]
    A = np.ones(N)
    tot = 0.0
    for k in range(n):
        tot += float((A * Val[k][:, 0]).mean())
        A = A * Prop[k][:, 0]
    return tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ext", default=str(Path.home() / "qwen-opt/tree/ext"))
    ap.add_argument("--T", type=float, default=1.0)
    ap.add_argument("--top-k", type=int, default=20)
    ap.add_argument("--dt", default="1.0", help="coupled draft temperature multipliers, comma list")
    ap.add_argument("--mc", type=int, default=64)
    ap.add_argument("--nodes", type=int, default=12)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    rng = np.random.default_rng(1234)
    hd, seqs = load(MT / "data/ext_p1", MT / "data/p1.idx.jsonl")
    toks = read_seqs_bin(str(MT / "data/p1.bin"))
    dts = [float(x) for x in a.dt.split(",")]
    G = defaultdict(lambda: defaultdict(list))     # group -> key -> list of arrays
    for f in sorted(Path(a.ext).glob("*.npz")):
        si = int(f.stem)
        s = seqs[si]
        z = np.load(f)
        T_, npr = int(z["n_tok"]), int(z["n_prompt"])
        tokens = toks[si]
        N = T_ - npr
        J = N - K + 1                                     # starts with the full K horizon
        if J <= 0:
            continue
        ids_all, p_all = sampler(s["top_id"], s["top_lp"], a.T, a.top_k, 0.95, 0.05)
        ids1, p1 = sampler(s["top_id"], s["top_lp"], 1.0, 20, 0.95, 0.05)
        j = np.arange(J)
        rec = {}
        for k in range(1, K + 1):
            row = j + k - 1
            x = tokens[npr - 1 + j + k]
            pT = prob_of(ids_all[row], p_all[row], x)
            p1x = prob_of(ids1[row], p1[row], x)
            w = np.where(p1x > 0, pT / np.maximum(p1x, 1e-300), 0.0)
            R = z["rank"][k - 1, :J].astype(np.int64)
            R = np.where((R < 0) | (R >= M), M, R)
            cand = z["top_id"][k - 1, :J, :M]
            Pc = prob_of(ids_all[row][:, None, :], p_all[row][:, None, :], cand)      # [J, M]
            rec[f"Pc{k}"] = Pc
            rec[f"PropG{k}"] = (R[:, None] == np.arange(M)[None, :]) * w[:, None]
            rec[f"w{k}"] = w
            rec[f"q1_{k}"] = np.exp(z["top_lp"][k - 1, :J, 0])
            rec[f"R{k}"] = R
            for dt in dts:
                dls = draft_filtered(z["top_lp"][k - 1, :J], a.top_k, 0.95, 0.05, a.T * dt)
                pi = coupled_rank_dist(ids_all[row], p_all[row], z["top_id"][k - 1, :J], dls, x, rng, a.mc)
                rec[f"C{dt}_{k}"] = pi[:, :M] * w[:, None]
        m = s["meta"]
        cat = f"{m['lang']}-{m['cat']}"
        te = np.flatnonzero(tokens == THINK_END)
        is_think = (npr + j) <= (te[0] if len(te) else len(tokens))
        for gname, msk in ((cat, np.ones(J, bool)), (f"{cat}/answer", ~is_think), ("all", np.ones(J, bool)),
                           ("prose", np.ones(J, bool) if m["cat"] == "prose" else np.zeros(J, bool))):
            if msk.any():
                for kk, v in rec.items():
                    G[gname][kk].append(v[msk])
    res = {}
    for g, d in G.items():
        cat = {kk: np.concatenate(v) for kk, v in d.items()}
        n = len(cat["w1"])
        Val = [cat[f"Pc{k}"] for k in range(1, K + 1)]
        Prop = [cat[f"PropG{k}"] for k in range(1, K + 1)]
        r = {"n": n}
        r["greedy_chain"] = {L: round(1 + chain_value(Val, Prop, L), 4) for L in range(1, K + 1)}
        bf = best_first(Val, Prop, None, a.nodes)
        r["greedy_tree"] = [{"n": i + 1, "path": list(p), "v": round(v, 4),
                             "tok": round(1 + sum(vv for _, vv in bf[: i + 1]), 4)} for i, (p, v) in enumerate(bf)]
        # depth-1 sibling value split by MTP top-1 confidence (dynamic width)
        r["d1_sib"] = {}
        for th in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.01):
            sel = cat["q1_1"] < th
            r["d1_sib"][th] = {"frac": round(float(sel.mean()), 4),
                               "gain_r1": round(float((sel * Val[0][:, 1]).mean()), 4),
                               "gain_r2": round(float((sel * Val[0][:, 2]).mean()), 4)}
        # per-depth sibling (rank 1 leaf under the greedy chain at depth k)
        A = np.ones(n)
        sib = []
        for k in range(K):
            sib.append(round(float((A * Val[k][:, 1]).mean()), 4))
            A = A * Prop[k][:, 0]
        r["sib_rank1_by_depth"] = sib
        # rank of the sampled token at the first rejected depth of the greedy chain-4 (realized, T-weighted)
        Rs = np.stack([cat[f"R{k}"] for k in range(1, 5)], 1)
        Ws = np.cumprod(np.stack([cat[f"w{k}"] for k in range(1, 5)], 1), 1)
        rej = Rs != 0
        has = rej.any(1)
        kf = rej.argmax(1)
        rr = Rs[np.arange(n), kf]
        ww = Ws[np.arange(n), kf]
        tot = float((ww * has).sum())
        r["first_reject"] = {"p_reject_within4": round(float((ww * has).sum() / Ws[:, 3].sum()), 4),
                             "rank_share": {int(q): round(float((ww * has * (rr == q)).sum() / tot), 4)
                                            for q in range(1, M + 1)},
                             "by_depth": {int(d + 1): round(float((ww * has * (kf == d)).sum() / tot), 4)
                                          for d in range(4)}}
        for dt in dts:
            C = [cat[f"C{dt}_{k}"] for k in range(1, K + 1)]
            r[f"coupled{dt}_chain"] = {L: round(1 + chain_value(C, C, L), 4) for L in range(1, K + 1)}
            bfc = best_first(C, C, None, a.nodes)
            r[f"coupled{dt}_tree"] = [{"n": i + 1, "path": list(p), "v": round(v, 4),
                                       "tok": round(1 + sum(vv for _, vv in bfc[: i + 1]), 4)}
                                      for i, (p, v) in enumerate(bfc)]
        res[g] = r
    txt = json.dumps(res, indent=1)
    if a.out:
        Path(a.out).write_text(txt)
    for g in sorted(res):
        r = res[g]
        print(f"== {g} n={r['n']} greedy chain {r['greedy_chain']}")
        print("   greedy tree tok by nodes:", [t["tok"] for t in r["greedy_tree"]])
        print("   greedy tree order:", [tuple(t["path"]) for t in r["greedy_tree"]])
        print("   sib rank1 by depth:", r["sib_rank1_by_depth"])
        print("   first reject (chain-4):", r["first_reject"])
        print("   d1 sib by q1<th:", r["d1_sib"])
        for dt in dts:
            print(f"   coupled DT={dt} chain {r[f'coupled{dt}_chain']}")
            print("     tree tok:", [t["tok"] for t in r[f"coupled{dt}_tree"]])
            print("     order:", [tuple(t["path"]) for t in r[f"coupled{dt}_tree"]])


if __name__ == "__main__":
    main()
