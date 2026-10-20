#!/usr/bin/env python3
"""Per-node MTP statistics along the REALIZED path, for offline tree / multi-draft ceilings (CPU only).

For every response start t and depth k = 1..K the MTP chain is fed the tokens the target actually sampled
(x_{t+1..t+k-1}), not its own argmax. Conditioned on the path being accepted the drafted tokens equal x, so these
are exactly the draft logits of every tree node that can ever be accepted (any node off the realized path is
rejected together with its whole subtree). Saved per sequence (npz):
  top_id [K, N, TOPN] int32 full-vocab ids of the MTP top-TOPN (draft vocab, descending)
  top_lp [K, N, TOPN] float32 MTP log-softmax (over the 64k draft vocab) of those ids
  rank   [K, N] int32  0-based rank of the realized x_{t+k} in the MTP logits (-1 = outside the draft vocab)
  lp_x   [K, N] float32 MTP log-prob of x_{t+k} (-inf if OOV)
N = n_tok - n_prompt starts t = n_prompt-1 .. n_tok-2 (start t predicts x_{t+1}); rows whose t+k > n_tok-1 are junk.
--greedy: feed the chain its own argmax instead (the server's greedy chain; needed to price off-path nodes of
dynamic trees). Then rank/lp_x are those of x only where the chain prefix equals the realized prefix.
usage: tree_extract.py --out DIR [--K 5] [--greedy] [--cats pl-prose,en-prose,...]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch

MT = Path.home() / "qwen-opt/mtp-train"
sys.path.insert(0, str(MT))
from analyze import load, read_seqs_bin  # noqa: E402
from mtp_torch import MTPHead, load_gguf_weights  # noqa: E402

TOPN = 40


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--K", type=int, default=5)
    ap.add_argument("--cats", default="pl-prose,en-prose,en-chat,pl-chat,en-tech,en-code,pl-tech,pl-code")
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--greedy", action="store_true")
    a = ap.parse_args()
    torch.set_num_threads(a.threads)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    hd, seqs = load(MT / "data/ext_p1", MT / "data/p1.idx.jsonl")
    toks = read_seqs_bin(str(MT / "data/p1.bin"))
    n_vd = int(hd["n_vocab_dft"])
    dvocab = np.loadtxt(Path.home() / "models/draft/draft_vocab_qwen38.txt", dtype=np.int64, max_rows=n_vd)
    to_dv = np.full(int(hd["n_vocab"]), -1, np.int64)
    to_dv[dvocab] = np.arange(n_vd)
    w = load_gguf_weights(str(Path.home() / "models/Qwen3.8-27B-UD-Q4_K_XL.gguf"), dvocab)
    tm = MTPHead(w, device="cpu", dtype=torch.float32)
    cats = a.cats.split(",")
    order = sorted(range(len(seqs)), key=lambda i: cats.index(f"{seqs[i]['meta']['lang']}-{seqs[i]['meta']['cat']}")
                   if f"{seqs[i]['meta']['lang']}-{seqs[i]['meta']['cat']}" in cats else 99)
    K = a.K
    for si in order:
        s = seqs[si]
        m = s["meta"]
        cat = f"{m['lang']}-{m['cat']}"
        if cat not in cats:
            continue
        f = out / f"{si:03d}.npz"
        if f.exists():
            continue
        t0 = time.time()
        tokens = toks[si]
        T, n_prompt = s["n_tok"], s["n_prompt"]
        with torch.no_grad():
            tok = torch.from_numpy(tokens)
            h = torch.from_numpy(np.asarray(s["h"])).float()
            h_prev = torch.cat([torch.zeros_like(h[:1]), h[:-1]], 0)
            hn_tf, kv_tf = tm.forward_tf(tok, h_prev, torch.arange(T))
            starts = torch.arange(n_prompt - 1, T - 1)
            N = len(starts)
            top_id = np.zeros((K, N, TOPN), np.int32)
            top_lp = np.zeros((K, N, TOPN), np.float32)
            rank = np.full((K, N), -1, np.int32)
            lp_x = np.full((K, N), -np.inf, np.float32)
            hcur = hn_tf[starts]
            kv_chain = []
            for k in range(1, K + 1):
                if k > 1:
                    if a.greedy:   # the server's chain: feed the previous depth's argmax (draft vocab top-1)
                        tin = torch.from_numpy(top_id[k - 2][:, 0].astype(np.int64))
                    else:          # realized path: feed the token the target sampled
                        tin = tok[torch.clamp(starts + k - 1, max=T - 1)]
                    hcur, kv = tm.forward_chain_step(tin, hcur, starts + k - 1, kv_tf, kv_chain)
                    kv_chain.append(kv)
                lg = tm.logits(hcur).float()
                lg = lg - torch.logsumexp(lg, -1, keepdim=True)
                v, i = lg.topk(TOPN, -1)
                top_id[k - 1] = dvocab[i.numpy()]
                top_lp[k - 1] = v.numpy()
                xi = torch.clamp(starts + k, max=T - 1).numpy()
                xd = torch.from_numpy(to_dv[tokens[xi]])
                ok = xd >= 0
                lx = torch.gather(lg, 1, xd.clamp(min=0)[:, None])[:, 0]
                rk = (lg > lx[:, None]).sum(-1)
                rank[k - 1] = torch.where(ok, rk, torch.full_like(rk, -1)).numpy()
                lp_x[k - 1] = torch.where(ok, lx, torch.full_like(lx, -float("inf"))).numpy()
                del lg
        np.savez(f, top_id=top_id, top_lp=top_lp, rank=rank, lp_x=lp_x, n_tok=T, n_prompt=n_prompt)
        print(json.dumps({"seq": si, "cat": cat, "id": m["id"], "N": N, "s": round(time.time() - t0, 1)}), flush=True)


if __name__ == "__main__":
    main()
