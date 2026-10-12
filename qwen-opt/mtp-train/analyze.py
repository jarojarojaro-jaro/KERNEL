"""Offline per-depth acceptance of an MTP head on target-generated text + PyTorch-vs-llama.cpp parity.

Inputs: mtp_extract output dir (h.f16, top.bin, chain.bin, d1*.f32, meta.txt) and the packer's idx jsonl.

Acceptance (greedy drafts verified against the target at the user's sampler, T=1 top-k 20 top-p 0.95 min-p 0.05):
  cum_k  = P(first k drafts accepted), averaged over all response start positions t
    realized : prod_{j<=k} [d_j == x_{t+j}]                    (x = the tokens the target actually sampled)
    expected : prod_{j<k} [d_j == x_{t+j}] * p'_{t+k-1}(d_k)   (same expectation, lower variance)
    oracle   : the same with the target's own argmax as the draft (ceiling of any greedy drafter)
    T=0      : prod_{j<k} [d_j == x_{t+j}] * [d_k == argmax p_{t+k-1}]  (exact-match agreement)
  tok/step = 1 + sum_k cum_k (n_draft = 4).
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

TOPK, TOPP, MINP = 20, 0.95, 0.05
THINK_END = 248069  # </think>


def load(dir_: Path, idx_path: Path):
    meta_lines = (dir_ / "meta.txt").read_text().split("\n")
    hdr = meta_lines[0].split()
    hd = {hdr[i]: hdr[i + 1] for i in range(0, len(hdr), 2)}
    n_embd, K, n_draft, n_vd = int(hd["n_embd"]), int(hd["topk"]), int(hd["n_draft"]), int(hd["n_vocab_dft"])
    seqs_meta = [tuple(map(int, l.split())) for l in meta_lines[1:] if l.strip()]
    idx = [json.loads(l) for l in open(idx_path)][: len(seqs_meta)]
    top = np.fromfile(dir_ / "top.bin", dtype=np.int32).reshape(-1, K, 2)
    top_id = top[..., 0]
    top_lp = top[..., 1].copy().view(np.float32)
    chain = np.fromfile(dir_ / "chain.bin", dtype=np.int32).reshape(-1, n_draft)
    h = np.memmap(dir_ / "h.f16", dtype=np.float16, mode="r").reshape(-1, n_embd)
    out = []
    o_r = o_h = 0
    for (n_tok, n_prompt), m in zip(seqs_meta, idx):
        assert m["n_tok"] == n_tok and m["n_prompt"] == n_prompt
        n_r = n_tok - 1 - (n_prompt - 1)
        out.append(dict(meta=m, n_tok=n_tok, n_prompt=n_prompt, top_id=top_id[o_r:o_r + n_r],
                        top_lp=top_lp[o_r:o_r + n_r], chain=chain[o_r:o_r + n_r], h=h[o_h:o_h + n_tok]))
        o_r += n_r
        o_h += n_tok
    assert o_r == len(chain) == len(top), (o_r, len(chain), len(top))
    return hd, out


def sampler_probs(top_id, top_lp):
    """User's sampler on the stored top-32: top-k 20 -> top-p 0.95 -> min-p 0.05 -> renormalize (T=1)."""
    p = np.exp(top_lp[:, :TOPK].astype(np.float64))
    p = p / p.sum(-1, keepdims=True)  # top-k renormalization (softmax over the kept logits)
    c = np.cumsum(p, -1)
    keep = (c - p) < TOPP  # minimal prefix with cumulative >= top_p
    keep &= p >= MINP * p[:, :1]
    p = np.where(keep, p, 0.0)
    return top_id[:, :TOPK], p / p.sum(-1, keepdims=True)


def prob_of(ids, probs, tok):
    m = ids == tok[:, None]
    return (probs * m).sum(-1)


def seq_metrics(s, drafts, tokens, qdist=None):
    """Per start position arrays for one sequence. drafts [N, n_draft] token ids;
    qdist: optional per-depth (token ids [N, 10], probs [N, 10]) of the head's draft distribution."""
    n_prompt, n_tok = s["n_prompt"], s["n_tok"]
    ids, probs = sampler_probs(s["top_id"], s["top_lp"])
    amax = ids[:, 0]
    pmax = probs[:, 0]
    nd = drafts.shape[1]
    N = n_tok - 1 - (n_prompt - 1) - (nd - 1)  # starts with all n_draft targets inside the sequence
    if N <= 0:
        return None
    starts = np.arange(n_prompt - 1, n_prompt - 1 + N)
    r = {k: np.zeros((N, nd)) for k in ("real", "exp", "oracle", "t0")}
    ok = np.ones(N, bool)
    ok_or = np.ones(N, bool)
    if qdist is not None:
        r["prob"] = np.zeros((N, nd))
    for j in range(nd):
        row = starts + j - (n_prompt - 1)  # top row of position t+j (predicts x_{t+j+1})
        x_next = tokens[starts + j + 1]
        d = drafts[:N, j]
        pd = prob_of(ids[row], probs[row], d)
        r["exp"][:, j] = ok * pd
        r["t0"][:, j] = ok * (d == amax[row])
        r["oracle"][:, j] = ok_or * pmax[row]
        if qdist is not None:
            # rejection-sampling acceptance sum_v min(p'(v), q(v)) of this depth's draft distribution
            # (q = softmax of the head's top-10 at T=1, as the server's draft sampler), on the greedy prefix
            q_ids, q_p = qdist[j]
            m = q_ids[:N, :, None] == ids[row][:, None, :]
            r["prob"][:, j] = ok * (np.minimum(q_p[:N, :, None], probs[row][:, None, :]) * m).sum((1, 2))
        ok = ok & (d == x_next)
        ok_or = ok_or & (amax[row] == x_next)
        r["real"][:, j] = ok
    return r


def summarize(rows):
    out = {}
    for k in ("real", "exp", "oracle", "t0", "prob"):
        if k not in rows[0]:
            continue
        cum = np.concatenate([r[k] for r in rows]).mean(0)
        out[k] = dict(cum=cum.tolist(), cond=(cum / np.concatenate([[1.0], cum[:-1]])).tolist(), tps=1 + cum.sum())
    out["n"] = int(sum(len(r["real"]) for r in rows))
    return out


def fmt(name, s):
    lines = [f"### {name} (n={s['n']} start positions)", "",
             "| estimator | cum d1 | d2 | d3 | d4 | cond d1 | d2 | d3 | d4 | tok/step |", "|---|---|---|---|---|---|---|---|---|---|"]
    for k, lab in (("real", "shipped, realized"), ("exp", "shipped, expected"), ("t0", "shipped, T=0 agreement"),
                   ("prob", "shipped, per-depth sum min(p',q10)"), ("oracle", "oracle greedy (target argmax)")):
        if k not in s:
            continue
        c, a = s[k]["cum"], s[k]["cond"]
        lines.append(f"| {lab} | " + " | ".join(f"{x:.3f}" for x in c) + " | " +
                     " | ".join(f"{x:.3f}" for x in a) + f" | {s[k]['tps']:.2f} |")
    return "\n".join(lines) + "\n"


def read_seqs_bin(path):
    a = np.fromfile(path, dtype=np.int32)
    o, out = 1, []
    for _ in range(int(a[0])):
        nt = int(a[o])
        out.append(a[o + 2:o + 2 + nt].astype(np.int64))
        o += 2 + nt
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="mtp_extract output dir")
    ap.add_argument("--seqs", required=True, help="pack_seqs prefix (reads .bin and .idx.jsonl)")
    ap.add_argument("--torch", action="store_true", help="also run the PyTorch mirror: parity + its own acceptance")
    ap.add_argument("--gguf", default=str(Path.home() / "models/Qwen3.8-27B-UD-Q4_K_XL.gguf"))
    ap.add_argument("--vocab", default=str(Path.home() / "models/draft/draft_vocab_qwen38.txt"))
    ap.add_argument("--kv-q4", action="store_true", help="emulate the q4_0 MTP KV cache in PyTorch")
    ap.add_argument("--dtype", default="float32", help="PyTorch mirror dtype (float32 | bfloat16)")
    ap.add_argument("--out", default=None, help="write the markdown report + json here (prefix)")
    a = ap.parse_args()
    d = Path(a.dir)
    hd, seqs = load(d, Path(a.seqs + ".idx.jsonl"))
    toks = read_seqs_bin(a.seqs + ".bin")
    n_vd, nd = int(hd["n_vocab_dft"]), int(hd["n_draft"])
    dvocab = np.loadtxt(a.vocab, dtype=np.int64, max_rows=n_vd)
    in_dv = np.zeros(int(hd["n_vocab"]), bool)
    in_dv[dvocab] = True

    groups, groups_t, oov = defaultdict(list), defaultdict(list), defaultdict(list)
    if a.torch:
        import torch
        from mtp_torch import MTPHead, load_gguf_weights
        w = load_gguf_weights(a.gguf, dvocab)
        tm = MTPHead(w, dtype=getattr(torch, a.dtype))
        tm.dvocab_t = torch.from_numpy(dvocab).cuda()
        par = dict(n=0, top1=0, maxabs=0.0, rel=[], hrel=[])
        agree = np.zeros(nd)
        agree_cond = np.zeros(nd)
        agree_n = 0
        n_par_seqs, par_max = int(hd["parity_seqs"]), int(hd["parity_max"])
        d1 = np.fromfile(d / "d1.f32", dtype=np.float32).reshape(-1, n_vd)
        d1h = np.fromfile(d / "d1h.f32", dtype=np.float32).reshape(-1, int(hd["n_embd"]))
        o_par = 0

    for si, s in enumerate(seqs):
        tokens = toks[si]
        m = s["meta"]
        keys = ["all", m["lang"], f"{m['lang']}-{m['cat']}"]
        r = seq_metrics(s, s["chain"], tokens)
        if r is None:
            continue
        # segment of the predicted token x_{t+1}: reasoning (up to and incl. </think>) or answer
        n_st = len(r["real"])
        starts = np.arange(s["n_prompt"] - 1, s["n_prompt"] - 1 + n_st)
        te = np.flatnonzero(tokens == THINK_END)
        is_think = starts + 1 <= (te[0] if len(te) else len(tokens))
        segs = ((f"{m['lang']}-think", is_think), (f"{m['lang']}-answer", ~is_think))
        resp = tokens[s["n_prompt"]:]
        resp_think = np.arange(s["n_prompt"], s["n_tok"]) <= (te[0] if len(te) else len(tokens))
        for k in keys:
            groups[k].append(r)
            oov[k].append(~in_dv[resp])
        for k, msk in segs:
            groups[k].append({kk: v[msk] for kk, v in r.items()})
            oov[k].append(~in_dv[resp[resp_think if k.endswith("think") else ~resp_think]])
        if not a.torch:
            continue
        h = torch.from_numpy(np.asarray(s["h"])).cuda().float()
        ids_t, logits, hn_tf = tm.draft_chain(torch.from_numpy(tokens).cuda(), h, s["n_prompt"], nd, a.kv_q4)
        dr_t = dvocab[ids_t.cpu().numpy()]
        qdist = []
        for lg in logits:
            qv, qi = lg.topk(10, -1)
            qdist.append((dvocab[qi.cpu().numpy()], torch.softmax(qv, -1).cpu().numpy().astype(np.float64)))
        rt = seq_metrics(s, dr_t, tokens, qdist)
        for k in keys:
            groups_t[k].append(rt)
        for k, msk in segs:
            groups_t[k].append({kk: v[msk] for kk, v in rt.items()})
        eq = dr_t == s["chain"]
        agree += eq.sum(0)
        agree_cond += np.cumprod(eq, 1).sum(0)
        agree_n += len(eq)
        if si < n_par_seqs:
            n_p = min(par_max, s["n_tok"] - 1 - (s["n_prompt"] - 1))
            ref = torch.from_numpy(d1[o_par:o_par + n_p]).cuda()
            mine = logits[0][:n_p]
            par["n"] += n_p
            par["top1"] += int((ref.argmax(-1) == mine.argmax(-1)).sum())
            par["maxabs"] = max(par["maxabs"], float((ref - mine).abs().max()))
            par["rel"].append(float((ref - mine).norm() / ref.norm()))
            href = torch.from_numpy(d1h[o_par:o_par + n_p]).cuda()
            hmine = hn_tf[s["n_prompt"] - 1:s["n_prompt"] - 1 + n_p]
            par["hrel"].append(float((href - hmine).norm() / href.norm()))
            o_par += n_p
        del logits, hn_tf, h

    rep = {"llama": {k: summarize(v) for k, v in groups.items()},
           "oov_resp": {k: float(np.concatenate(v).mean()) for k, v in oov.items()}}
    md = ["## Shipped MTP head, llama.cpp draft chain (n_draft=%d)\n" % nd]
    for k in sorted(groups, key=lambda x: (len(x), x)):
        md.append(fmt(f"{k} (resp tokens outside 64k draft vocab: {rep['oov_resp'][k] * 100:.1f}%)", rep["llama"][k]))
    if a.torch:
        rep["torch"] = {k: summarize(v) for k, v in groups_t.items()}
        rep["parity"] = dict(d1_positions=par["n"], d1_top1_agree=par["top1"] / max(1, par["n"]),
                             d1_logit_maxabs=par["maxabs"], d1_logit_relL2=float(np.mean(par["rel"])),
                             d1_hnextn_relL2=float(np.mean(par["hrel"])),
                             chain_token_agree=(agree / agree_n).tolist(),
                             chain_prefix_agree=(agree_cond / agree_n).tolist(), chain_n=agree_n)
        md.append("## PyTorch mirror vs llama.cpp\n\n```\n" + json.dumps(rep["parity"], indent=1) + "\n```\n")
        md.append("## PyTorch mirror (fp32) acceptance incl. probabilistic estimator\n")
        for k in sorted(groups_t, key=lambda x: (len(x), x)):
            md.append(fmt(f"torch {k}", rep["torch"][k]))
    text = "\n".join(md)
    print(text)
    if a.out:
        Path(a.out + ".md").write_text(text)
        Path(a.out + ".json").write_text(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
