#!/usr/bin/env python3
"""R68b: coupled Gumbel gap as a draft-time confidence for adaptive MTP depth (offline, CPU only; data of 24s).
Policy: draft depth 1 always; continue to depth k+1 only if the perturbed draft-score gap at depth k >= tau (max 5).
Depths are independent given the realized path, so sample s is paired across depths. Cost: 27.6 ms at depth 4,
+-1.6 ms per draft level (0.75 ms MTP pass + 0.85 ms verify row; 24q/24s cost models)."""
import sys
from collections import defaultdict
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path.home() / "KERNEL/product/research/24s-drzewa"))
import tree_ceiling as tc
sys.path.insert(0, str(Path(__file__).parent))
from gumbo_sim import rank_gap
K, S = 5, 32
rng = np.random.default_rng(681)
hd, seqs = tc.load(tc.MT / "data/ext_p1", tc.MT / "data/p1.idx.jsonl")
toks = tc.read_seqs_bin(str(tc.MT / "data/p1.bin"))
acc = defaultdict(lambda: defaultdict(list))
for f in sorted((Path.home() / "qwen-opt/tree/ext").glob("*.npz")):
    si = int(f.stem); s = seqs[si]; z = np.load(f)
    T_, npr = int(z["n_tok"]), int(z["n_prompt"]); tokens = toks[si]; J = T_ - npr - K + 1
    if J <= 0: continue
    ids_all, p_all = tc.sampler(s["top_id"], s["top_lp"], 1.0, 20, 0.95, 0.05)
    j = np.arange(J); R = []; G = []
    for k in range(1, K + 1):
        row = j + k - 1; x = tokens[npr - 1 + j + k]
        dls = tc.draft_filtered(z["top_lp"][k - 1, :J], 20, 0.95, 0.05, 1.0)
        r, g = rank_gap(ids_all[row], p_all[row], z["top_id"][k - 1, :J], dls, x, rng, S)
        R.append(r == 0); G.append(g)
    R = np.stack(R, -1); G = np.stack(G, -1)          # [J,S,K]
    m = s["meta"]; cat = f"{m['lang']}-{m['cat']}"
    for gname in (cat, "all"):
        acc[gname]["R"].append(R); acc[gname]["G"].append(G)
for g in sorted(acc):
    R = np.concatenate(acc[g]["R"]); G = np.concatenate(acc[g]["G"])
    acc_run = np.cumprod(R, -1)                       # accepted through depth k
    def evalp(dmin, dmax, tau):
        # drafted depth d: 1 + number of consecutive gaps >= tau among depths dmin..dmax-1
        cont = G >= tau
        d = np.full(R.shape[:2], dmax)
        for k in range(dmin, dmax):                   # depth k (1-based) decides on drafting k+1
            stop = ~cont[:, :, k - 1] & (d == dmax)
            d = np.where(stop, k, d)
        tok = 1 + sum((acc_run[:, :, k - 1] * (d >= k)).mean() for k in range(1, dmax + 1))
        import os
        if os.environ.get('COSTB'):
            ms = 27.6 + (dmax - 4) * 0.75 + (d.mean() - 4) * 0.85   # B: draft graph always runs dmax passes
        else:
            ms = 27.6 + (d.mean() - 4) * 1.6                         # A: early exit of the draft chain
        return tok, d.mean(), ms
    b_tok, _, b_ms = evalp(4, 4, 0)
    print(f"== {g} n={R.shape[0]} chain-4 tok {b_tok:.4f}")
    for dmin, dmax in ((4, 5), (3, 5), (2, 5)):
        best = None
        for tau in (0, 0.5, 1, 1.5, 2, 3, 4, 6, 1e9):
            tok, dm, ms = evalp(dmin, dmax, tau)
            net = (tok / ms) / (b_tok / b_ms) - 1
            print(f"   depth {dmin}..{dmax} tau={tau:<6} mean depth {dm:.2f} tok {tok:.4f} net {net*100:+.2f}%")
