#!/usr/bin/env python3
"""Report 40, CPU only: per-depth acceptance of the MTP chain on prose at T=1 (greedy draft and Gumbel-coupled draft,
production sampler top-k 20 / top-p 0.95 / min-p 0.05), where the chain breaks by token class, and ceilings.

Inputs: tree_extract.py / ext_head.py npz (MTP logits on the realized path, K=5) + phase-1 teacher data (target
top-32 log-probs, sampled tokens). Estimators as in 24s tree_ceiling.py (realized-path indicators for the prefix,
expectation at the last level; coupled = posterior P(the draft's perturbed argmax is the sampled x)).

Per start t and depth k (x = x_{t+k}):
  greedy  a_k = 1[MTP argmax == x]  (prefix)    v_k = p'(MTP argmax)   (last level)
  coupled a_k = v_k = pi_k(rank 0)
  oracle  a_k = 1[target argmax == x]            v_k = p'max           (greedy draft that always knows the target top-1)
  maxcpl  v_k = sum_y min(q'(y), p'(y))   (maximal coupling of the current head's filtered q' with p': what an exact
          rejection-style coupling could get from this head; prefix uses the same value as a propagation factor)
S_k = E[prod_{i<k} a_i * v_k]; tok/step(n) = 1 + sum_{k<=n} S_k. Break attribution: loss at depth k =
E[prod_{i<k} a_i * (1 - v_k)], assigned to the class of x_{t+k} (where the chain breaks).
usage: pa_offline.py [--ext DIR] [--out JSON] [--mc 64]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MT = Path.home() / "qwen-opt/mtp-train"
sys.path.insert(0, str(MT))
sys.path.insert(0, str(Path.home() / "qwen-opt/tree"))
sys.path.insert(0, str(HERE))
from analyze import load, read_seqs_bin  # noqa: E402
from tree_ceiling import coupled_rank_dist, draft_filtered, prob_of, sampler  # noqa: E402
import tokclass  # noqa: E402

THINK_END = 248069
K = 5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ext", default=str(Path.home() / "qwen-opt/tree/ext"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--mc", type=int, default=64)
    ap.add_argument("--cats", default="pl-prose,en-prose,pl-chat,en-chat")
    ap.add_argument("--data", default="", help="mtp_extract dir with seqs.bin + idx.jsonl (default: phase-1 ext_p1)")
    a = ap.parse_args()
    rng = np.random.default_rng(1234)
    if a.data:
        hd, seqs = load(Path(a.data), Path(a.data) / "idx.jsonl")
        toks = read_seqs_bin(str(Path(a.data) / "seqs.bin"))
    else:
        hd, seqs = load(MT / "data/ext_p1", MT / "data/p1.idx.jsonl")
        toks = read_seqs_bin(str(MT / "data/p1.bin"))
    cls, strs = tokclass.classes(int(hd["n_vocab"]))
    cats = a.cats.split(",")
    G = defaultdict(lambda: defaultdict(list))
    for f in sorted(Path(a.ext).glob("*.npz")):
        si = int(f.stem)
        s = seqs[si]
        m = s["meta"]
        cat = f"{m['lang']}-{m['cat']}"
        if cat not in cats:
            continue
        z = np.load(f)
        T_, npr = int(z["n_tok"]), int(z["n_prompt"])
        tokens = toks[si]
        J = T_ - npr - K + 1
        if J <= 0:
            continue
        ids, p = sampler(s["top_id"], s["top_lp"], 1.0, 20, 0.95, 0.05)
        j = np.arange(J)
        rec = {}
        for k in range(1, K + 1):
            row = j + k - 1
            x = tokens[npr - 1 + j + k]
            R = z["rank"][k - 1, :J]
            d0 = z["top_id"][k - 1, :J, 0]
            rec[f"aG{k}"] = (R == 0).astype(np.float64)
            rec[f"vG{k}"] = prob_of(ids[row], p[row], d0)
            rec[f"aO{k}"] = (ids[row][:, 0] == x).astype(np.float64)
            rec[f"vO{k}"] = p[row][:, 0]
            dls = draft_filtered(z["top_lp"][k - 1, :J], 20, 0.95, 0.05, 1.0)
            pi = coupled_rank_dist(ids[row], p[row], z["top_id"][k - 1, :J], dls, x, rng, a.mc)
            rec[f"vC{k}"] = pi[:, 0]
            q = np.where(np.isfinite(dls), np.exp(dls), 0.0)
            q = q / q.sum(-1, keepdims=True)
            dids = z["top_id"][k - 1, :J]
            pd = prob_of(ids[row][:, None, :], p[row][:, None, :], dids)             # p' at draft candidates [J,40]
            rec[f"vM{k}"] = np.minimum(q, pd).sum(-1)
            rec[f"cx{k}"] = cls[x].astype(np.int64)
            rec[f"cd{k}"] = cls[d0].astype(np.int64)
            rec[f"px{k}"] = prob_of(ids[row], p[row], x)
            rec[f"q1{k}"] = np.exp(z["top_lp"][k - 1, :J, 0])
        te = np.flatnonzero(tokens == THINK_END)
        is_think = (npr + j) <= (te[0] if len(te) else -1)
        groups = [(cat, np.ones(J, bool)), (f"{cat}/answer", ~is_think)]
        if m["cat"] == "prose":
            groups += [("prose", np.ones(J, bool)), ("prose/answer", ~is_think)]
        for g, msk in groups:
            if msk.any():
                for kk, v in rec.items():
                    G[g][kk].append(v[msk])
    res = {}
    NC = len(tokclass.CLASSES)
    for g, d in G.items():
        c = {kk: np.concatenate(v) for kk, v in d.items()}
        n = len(c["aG1"])
        r = {"n": n}
        # t0: acceptance at T=0 on a greedy-generated path (x = target argmax): 1[MTP argmax == x]
        for tag, prop in (("greedy", "aG"), ("coupled", "vC"), ("oracle", "aO"), ("maxcpl", "vM"), ("t0", "aG")):
            val = {"greedy": "vG", "coupled": "vC", "oracle": "vO", "maxcpl": "vM", "t0": "aG"}[tag]
            A = np.ones(n)
            S, loss = [], np.zeros((K, NC))
            for k in range(1, K + 1):
                v = c[f"{val}{k}"]
                S.append(float((A * v).mean()))
                lk = A * (1 - v)
                loss[k - 1] = np.bincount(c[f"cx{k}"], weights=lk, minlength=NC) / n
                A = A * c[f"{prop}{k}"]
            cond = [S[0]] + [S[k] / S[k - 1] for k in range(1, K)]
            r[tag] = {"S": [round(x, 4) for x in S], "cond": [round(x, 4) for x in cond],
                      "tok": {L: round(1 + sum(S[:L]), 4) for L in range(1, K + 1)},
                      "break_by_class_n4": {tokclass.CLASSES[i]: round(float(loss[:4, i].sum() / loss[:4].sum()), 4)
                                            for i in range(NC)},
                      "break_by_depth_n4": [round(float(loss[k].sum() / loss[:4].sum()), 4) for k in range(4)]}
        # per-position (depth 1) stats by class of the sampled token
        cx = c["cx1"]
        r["pos_by_class"] = {}
        for i, nm in enumerate(tokclass.CLASSES):
            sel = cx == i
            if sel.sum() == 0:
                continue
            r["pos_by_class"][nm] = {"share": round(float(sel.mean()), 4),
                                     "acc_greedy_d1": round(float(c["vG1"][sel].mean()), 4),
                                     "acc_coupled_d1": round(float(c["vC1"][sel].mean()), 4),
                                     "p_target_x": round(float(c["px1"][sel].mean()), 4),
                                     "pmax_target": round(float(c["vO1"][sel].mean()), 4),
                                     "acc_coupled_d2": round(float(c["vC2"][c["cx2"] == i].mean()), 4)}
        # greedy breaks at depth 1: what did the draft propose vs what the target sampled (classes)
        brk = c["aG1"] == 0
        tab = np.zeros((NC, NC))
        np.add.at(tab, (c["cx1"][brk], c["cd1"][brk]), 1)
        tab /= max(1, brk.sum())
        r["d1_break_x_vs_draft"] = {tokclass.CLASSES[i]: {tokclass.CLASSES[jj]: round(float(tab[i, jj]), 4)
                                                          for jj in range(NC) if tab[i, jj] > 0.004}
                                    for i in range(NC) if tab[i].sum() > 0.004}
        # target entropy floor: share of depth-1 positions where target top-1 prob < 0.5 and their acceptance
        pm = c["vO1"]
        r["flat"] = {th: {"share": round(float((pm < th).mean()), 4),
                          "acc_coupled": round(float(c["vC1"][pm < th].mean()), 4),
                          "acc_greedy": round(float(c["vG1"][pm < th].mean()), 4)} for th in (0.3, 0.5, 0.7, 0.9)}
        r["oov_rate"] = round(float((cx == tokclass.CLASSES.index("oov")).mean()), 4)
        res[g] = r
    txt = json.dumps(res, indent=1, ensure_ascii=False)
    if a.out:
        Path(a.out).write_text(txt)
    for g in sorted(res):
        r = res[g]
        print(f"== {g} n={r['n']} oov {r['oov_rate']}")
        for tag in ("greedy", "coupled", "oracle", "maxcpl", "t0"):
            print(f"   {tag:8s} cond {r[tag]['cond']} tok n1..5 {list(r[tag]['tok'].values())}")
        print("   coupled break by class n4:", r["coupled"]["break_by_class_n4"], "depth", r["coupled"]["break_by_depth_n4"])


if __name__ == "__main__":
    main()
