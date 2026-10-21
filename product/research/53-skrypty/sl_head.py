#!/usr/bin/env python3
"""Report 53 (E52b), CPU only: low-rank shortlist scorer for the MTP draft head over the FULL 248k vocab.

z~ = A (B hn)  (A [V, r], B [r, d]),  C = TopK(z~, K),  z_C = W_C hn  (W = target output.weight, exact).

Phases (all write under --work):
  dump-eval  MTP chain on the realized path of e0x (K=5 depths, like 40/ext_head.py): hn fp16 per sequence
  dump-train teacher-forced MTP hn (depth 1) on all positions of ext_p1 (phase-1 data, other prompts than E0)
  wfull      dequantize output.weight (Q6_K) -> fp16 npy (cache)
  targets    exact top-TT ids/logits + logsumexp of W hn for the training states
  fit        init A, B by SVD of W Sigma^{1/2} (Sigma = E[h h^T] of training states), then forward-KL fine-tune
             (exact top-TT distribution vs softmax(z~) over the full vocab) + hinge on the true top-20 vs the K-th score
  eval       on e0x: recall of the full-vocab top-1/top-20 in C; writes ext_head-format npz dirs for
             ext_full (full 248k head) and ext_sl (shortlist head), consumed by 40/pa_offline.py
  export     factors -> raw file for the GPU path (LLAMA_DRAFT_SHORTLIST_FACTORS)
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys
import time
from pathlib import Path

import numpy as np
import torch

MT = Path.home() / "qwen-opt/mtp-train"
sys.path.insert(0, str(MT))
from analyze import load, read_seqs_bin  # noqa: E402
from mtp_torch import CACHE, MTPHead, gguf, load_gguf_weights  # noqa: E402
from gguf.quants import dequantize  # noqa: E402

GGUF = Path.home() / "models/Qwen3.8-27B-UD-Q4_K_XL.gguf"
DVOCAB = Path.home() / "models/draft/draft_vocab_qwen38.txt"
E0X = Path.home() / "qwen-opt/prose-accept/e0x"
TOPN = 40
TT = 256


def mtp(n_vd=65536):
    dvocab = np.loadtxt(DVOCAB, dtype=np.int64, max_rows=n_vd)
    w = load_gguf_weights(str(GGUF), dvocab)
    return MTPHead(w, device="cpu", dtype=torch.float32), dvocab


def wfull(work: Path) -> np.ndarray:
    f = CACHE / f"{GGUF.stem}.output_full.f16.npy"
    if not f.exists():
        t = {t.name: t for t in gguf.GGUFReader(str(GGUF)).tensors}["output.weight"]
        data = np.asarray(t.data)
        out = np.lib.format.open_memmap(f, mode="w+", dtype=np.float16, shape=(data.shape[0], int(t.shape[0])))
        for i in range(0, data.shape[0], 8192):
            out[i:i + 8192] = dequantize(data[i:i + 8192], t.tensor_type).astype(np.float16)
        out.flush()
        del out
    return np.load(f, mmap_mode="r")


def dump_eval(a, work: Path):
    hd, seqs = load(E0X, E0X / "idx.jsonl")
    toks = read_seqs_bin(str(E0X / "seqs.bin"))
    tm, _ = mtp()
    out = work / "hn_eval"
    out.mkdir(parents=True, exist_ok=True)
    K = 5
    for si, s in enumerate(seqs):
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
            hcur = hn_tf[starts]
            kv_chain, hs = [], []
            for k in range(1, K + 1):
                if k > 1:
                    tin = tok[torch.clamp(starts + k - 1, max=T - 1)]
                    hcur, kv = tm.forward_chain_step(tin, hcur, starts + k - 1, kv_tf, kv_chain)
                    kv_chain.append(kv)
                hs.append(hcur.half().numpy())
        np.savez(f, hn=np.stack(hs), n_tok=T, n_prompt=n_prompt)
        print(json.dumps({"seq": si, "N": len(starts), "s": round(time.time() - t0, 1)}), flush=True)


def dump_train(a, work: Path):
    hd, seqs = load(MT / "data/ext_p1", MT / "data/p1.idx.jsonl")
    toks = read_seqs_bin(str(MT / "data/p1.bin"))
    tm, _ = mtp()
    hs = []
    for si, s in enumerate(seqs):
        T = s["n_tok"]
        with torch.no_grad():
            h = torch.from_numpy(np.asarray(s["h"])).float()
            h_prev = torch.cat([torch.zeros_like(h[:1]), h[:-1]], 0)
            hn_tf, _ = tm.forward_tf(torch.from_numpy(toks[si]), h_prev, torch.arange(T))
        hs.append(hn_tf.half().numpy())
        print(json.dumps({"seq": si, "T": T}), flush=True)
    np.save(work / "hn_train.npy", np.concatenate(hs))


def exact_top(W16: np.ndarray, H: torch.Tensor, tt: int, chunk_v: int = 32768):
    """Exact top-tt ids/logits and logsumexp of W h for H [n, d] (fp32), streaming W in vocab chunks."""
    n = H.shape[0]
    best_v = torch.full((n, tt), -float("inf"))
    best_i = torch.zeros((n, tt), dtype=torch.int64)
    m = torch.full((n,), -float("inf"))
    s = torch.zeros(n)
    for v0 in range(0, W16.shape[0], chunk_v):
        Wc = torch.from_numpy(np.asarray(W16[v0:v0 + chunk_v], dtype=np.float32))
        z = H @ Wc.T
        mz = torch.maximum(m, z.max(-1).values)
        s = s * torch.exp(m - mz) + torch.exp(z - mz[:, None]).sum(-1)
        m = mz
        v, i = z.topk(min(tt, z.shape[1]), -1)
        cv = torch.cat([best_v, v], 1)
        ci = torch.cat([best_i, i + v0], 1)
        best_v, j = cv.topk(tt, -1)
        best_i = torch.gather(ci, 1, j)
    return best_i, best_v, m + torch.log(s)


def targets(a, work: Path):
    W16 = wfull(work)
    H = np.load(work / "hn_train.npy", mmap_mode="r")
    n = H.shape[0]
    ids = np.zeros((n, TT), np.int32)
    lg = np.zeros((n, TT), np.float32)
    lse = np.zeros(n, np.float32)
    for i in range(0, n, 2048):
        t0 = time.time()
        bi, bv, l = exact_top(W16, torch.from_numpy(np.asarray(H[i:i + 2048], np.float32)), TT)
        ids[i:i + 2048], lg[i:i + 2048], lse[i:i + 2048] = bi.numpy(), bv.numpy(), l.numpy()
        print(json.dumps({"targets": i, "n": n, "s": round(time.time() - t0, 1)}), flush=True)
    np.savez(work / "targets.npz", ids=ids, lg=lg, lse=lse)


def fit(a, work: Path):
    r, K = a.rank, a.K
    W16 = wfull(work)
    H = torch.from_numpy(np.load(work / "hn_train.npy").astype(np.float32))
    tz = np.load(work / "targets.npz")
    tid, tlg, tlse = (torch.from_numpy(tz[k]) for k in ("ids", "lg", "lse"))
    tid = tid.long()
    n, d = H.shape
    V = W16.shape[0]
    # init: rank-r approximation of the map h -> W h under the data covariance (W Sigma^{1/2} = U S V^T)
    f_init = work / f"init_r{r}.pt"
    if f_init.exists():
        A, B = torch.load(f_init)
    else:
        t0 = time.time()
        Sig = (H.T @ H) / n
        ev, Q = torch.linalg.eigh(Sig.double())
        ev = ev.clamp(min=ev.max() * 1e-8)
        Sh = (Q * ev.sqrt()) @ Q.T
        Shi = (Q / ev.sqrt()) @ Q.T
        Wt = torch.from_numpy(np.asarray(W16, dtype=np.float32))     # [V, d] fp32, 5 GB
        M = Wt @ Sh.float()
        U, S, Vh = torch.svd_lowrank(M, q=r + 64, niter=3)
        A = (U[:, :r] * S[:r]).contiguous()                          # [V, r]
        B = (Vh[:, :r].T @ Shi.float()).contiguous()                 # [r, d]
        del Wt, M
        torch.save((A, B), f_init)
        print(json.dumps({"init_s": round(time.time() - t0, 1)}), flush=True)
    rep = recall_train(A, B, H, tid, K, n_eval=4096)
    print(json.dumps({"init_recall": rep}), flush=True)
    if a.steps > 0:
        A = torch.nn.Parameter(A.clone())
        B = torch.nn.Parameter(B.clone())
        opt = torch.optim.Adam([A, B], lr=a.lr)
        g = torch.Generator().manual_seed(0)
        hold = 4096
        idx_tr = torch.arange(hold, n)
        pt = torch.softmax(tlg[:, :TT], -1)   # exact distribution restricted to the exact top-TT (renormalized)
        for step in range(a.steps):
            b = idx_tr[torch.randint(len(idx_tr), (a.bs,), generator=g)]
            zt = (H[b] @ B.T) @ A.T                                    # [bs, V]
            lz = torch.log_softmax(zt, -1)
            kl = -(pt[b] * torch.gather(lz, 1, tid[b])).sum(-1).mean()
            # hinge: true top-20 should score above the K-th low-rank score by a margin
            kth = zt.topk(K, -1).values[:, -1].detach()
            t20 = torch.gather(zt, 1, tid[b, :20])
            hinge = torch.relu(kth[:, None] + a.margin - t20).mean()
            loss = kl + a.hw * hinge
            opt.zero_grad()
            loss.backward()
            opt.step()
            if step % 100 == 0 or step == a.steps - 1:
                print(json.dumps({"step": step, "kl": round(float(kl), 4), "hinge": round(float(hinge), 4)}), flush=True)
            if step % 500 == 499:
                print(json.dumps({"recall": recall_train(A.detach(), B.detach(), H, tid, K, 4096)}), flush=True)
        A, B = A.detach(), B.detach()
    torch.save((A, B), work / f"ab_r{r}.pt")
    print(json.dumps({"final_recall_holdout": recall_train(A, B, H, tid, K, 4096)}), flush=True)


@torch.no_grad()
def recall_train(A, B, H, tid, K, n_eval):
    zt = (H[:n_eval] @ B.T) @ A.T
    C = zt.topk(K, -1).indices
    inC = (tid[:n_eval, :20, None] == C[:, None, :]).any(-1)
    return {"top1": round(float(inC[:, 0].float().mean()), 5), "top20_all": round(float(inC.all(-1).float().mean()), 5),
            "top20_frac": round(float(inC.float().mean()), 5)}


@torch.no_grad()
def evaluate(a, work: Path):
    hd, seqs = load(E0X, E0X / "idx.jsonl")
    toks = read_seqs_bin(str(E0X / "seqs.bin"))
    W16 = wfull(work)
    Wt = torch.from_numpy(np.asarray(W16, dtype=np.float32))
    cfgs = []
    for c in a.cfgs.split(","):                                      # "ab.pt:K"
        ab, K = c.split(":")
        A, B = torch.load(work / ab)
        tag = f"{Path(ab).stem}_K{K}"
        (work / f"ext_sl_{tag}").mkdir(exist_ok=True)
        cfgs.append(dict(A=A, B=B, K=int(K), tag=tag, o=work / f"ext_sl_{tag}",
                         stats={"top1": [], "top5_all": [], "top20_all": [], "top20_frac": [], "x_in_C": []}))
    o_full = work / "ext_full"
    o_full.mkdir(exist_ok=True)
    xfull = []
    for f in sorted((work / "hn_eval").glob("*.npz")):
        si = int(f.stem)
        if a.part and si % int(a.part.split("/")[1]) != int(a.part.split("/")[0]):
            continue
        if (o_full / f.name).exists() and all((c["o"] / f.name).exists() for c in cfgs) and not a.stats:
            continue                                             # resume (recall stats then cover the new part only)
        z = np.load(f)
        hn = torch.from_numpy(z["hn"].astype(np.float32))        # [Kd, N, d]
        Kd, N, _ = hn.shape
        T, npr = int(z["n_tok"]), int(z["n_prompt"])
        tokens = toks[si]
        do_full = not (o_full / f.name).exists()
        new = lambda: ({k: np.zeros((Kd, N, TOPN), np.int32 if k == "top_id" else np.float32) for k in ("top_id", "top_lp")},  # noqa: E731
                       np.full((Kd, N), -1, np.int32), np.full((Kd, N), -np.inf, np.float32))
        F, rF, lF = new()
        outs = [new() for _ in cfgs]
        starts = np.arange(npr - 1, T - 1)
        for k in range(Kd):
            h = hn[k]
            lg = h @ Wt.T                                            # [N, V] exact full logits
            lg = lg - torch.logsumexp(lg, -1, keepdim=True)
            x = torch.from_numpy(tokens[np.minimum(starts + k + 1, T - 1)].astype(np.int64))
            lx = lg.gather(1, x[:, None])[:, 0]
            valid = np.arange(N) + k + 1 <= T - 1 - (npr - 1)
            if do_full:
                v, i = lg.topk(TOPN, -1)
                F["top_id"][k], F["top_lp"][k] = i.numpy(), v.numpy()
                rF[k] = (lg > lx[:, None]).sum(-1).numpy()
                lF[k] = lx.numpy()
            t20 = lg.topk(20, -1).indices
            for c, (S, rS, lS) in zip(cfgs, outs):
                K = c["K"]
                zt = (h @ c["B"].T) @ c["A"].T
                C = zt.topk(K, -1).indices                           # [N, K]
                lc = lg.gather(1, C)                                 # exact logits on C (normalization irrelevant)
                lc = lc - torch.logsumexp(lc, -1, keepdim=True)
                v, j = lc.topk(min(TOPN, K), -1)
                S["top_id"][k, :, :v.shape[1]], S["top_lp"][k, :, :v.shape[1]] = C.gather(1, j).numpy(), v.numpy()
                if v.shape[1] < TOPN:
                    S["top_lp"][k, :, v.shape[1]:] = -np.inf
                xin = (C == x[:, None])
                ok = xin.any(-1)
                lxc = torch.where(ok, (lc * xin).sum(-1), torch.full_like(lx, -float("inf")))
                rS[k] = torch.where(ok, (lc > lxc[:, None]).sum(-1), torch.full_like(ok, -1, dtype=torch.int64)).numpy()
                lS[k] = lxc.numpy()
                inC = (t20[:, :, None] == C[:, None, :]).any(-1)
                st = c["stats"]
                st["top1"].append(inC[:, 0].numpy()[valid])
                st["top5_all"].append(inC[:, :5].all(-1).numpy()[valid])
                st["top20_all"].append(inC.all(-1).numpy()[valid])
                st["top20_frac"].append(inC.float().mean(-1).numpy()[valid])
                st["x_in_C"].append(ok.numpy()[valid])
                del zt
            xfull.append(((lg > lx[:, None]).sum(-1) < 40).numpy()[valid])
            del lg
        if do_full:
            np.savez(o_full / f.name, top_id=F["top_id"], top_lp=F["top_lp"], rank=rF, lp_x=lF, n_tok=T, n_prompt=npr)
        for c, (S, rS, lS) in zip(cfgs, outs):
            np.savez(c["o"] / f.name, top_id=S["top_id"], top_lp=S["top_lp"], rank=rS, lp_x=lS, n_tok=T, n_prompt=npr)
        print(json.dumps({"seq": si}), flush=True)
    for c in cfgs:
        rep = {k: round(float(np.concatenate(v).mean()), 5) for k, v in c["stats"].items()}
        rep.update(tag=c["tag"], x_in_full_top40=round(float(np.concatenate(xfull).mean()), 5))
        print(json.dumps({"eval_recall": rep}), flush=True)
        (work / f"recall_{c['tag']}.json").write_text(json.dumps(rep, indent=1))


def export(a, work: Path):
    """raw factors for the GPU path: magic 'DSL1', u32 rank, u32 n_vocab, u32 n_embd, f32 B[r][d], f16 A[V][r]."""
    A, B = torch.load(work / a.ab)
    with open(a.out, "wb") as fo:
        fo.write(b"DSL1")
        fo.write(struct.pack("<III", B.shape[0], A.shape[0], B.shape[1]))
        fo.write(B.float().contiguous().numpy().tobytes())
        fo.write(A.half().contiguous().numpy().tobytes())
    print(a.out, os.path.getsize(a.out))


@torch.no_grad()
def ridge(a, work: Path):
    """Top-weighted least squares for A with B fixed (closed form, no SGD): per vocab row v
       min_a  sum_h (a.u_h - z_v(h))^2 + lam * sum_{h: v in exact top-TOPW(h)} (a.u_h - z_v(h))^2,   u_h = B h.
    The first term uses all logits implicitly (U^T Z = (H^T U)^T W^T), the second only the stored exact top entries."""
    W16 = wfull(work)
    A0, B = torch.load(work / a.ab)
    H = torch.from_numpy(np.load(work / "hn_train.npy").astype(np.float32))
    tz = np.load(work / "targets.npz")
    tw = a.topw
    tid = torch.from_numpy(tz["ids"][:, :tw].astype(np.int64))
    tlg = torch.from_numpy(tz["lg"][:, :tw])
    U = H @ B.T                                                   # [n, r]
    n, r = U.shape
    G = (U.T @ U).double()                                        # [r, r]
    HU = (H.T @ U)                                                # [d, r]
    V = W16.shape[0]
    rhs = torch.zeros(V, r)
    for v0 in range(0, V, 32768):
        rhs[v0:v0 + 32768] = torch.from_numpy(np.asarray(W16[v0:v0 + 32768], dtype=np.float32)) @ HU
    # per-row extra statistics from the top entries
    flat_v = tid.reshape(-1)
    flat_h = torch.arange(n).repeat_interleave(tw)
    flat_z = tlg.reshape(-1)
    rows, inv = torch.unique(flat_v, return_inverse=True)
    R = len(rows)
    S = torch.zeros(R, r, r)
    b = torch.zeros(R, r, dtype=torch.float64)
    for i in range(0, len(flat_v), 20000):
        uu = U[flat_h[i:i + 20000]]
        S.index_add_(0, inv[i:i + 20000], uu[:, :, None] * uu[:, None, :])
        b.index_add_(0, inv[i:i + 20000], (uu * flat_z[i:i + 20000, None]).double())
    Gi = torch.linalg.inv(G)
    A = (rhs.double() @ Gi).float()                               # plain LS for every row
    for lam in [float(x) for x in a.lams.split(",")]:
        An = A.clone()
        for i in range(0, R, 4096):
            M = G[None] + lam * S[i:i + 4096].double()
            y = rhs[rows[i:i + 4096]].double() + lam * b[i:i + 4096]
            An[rows[i:i + 4096]] = torch.linalg.solve(M, y).float()
        f = work / f"ridge_l{lam:g}_t{tw}.pt"
        torch.save((An, B), f)
        print(json.dumps({"ridge": f.name, "rows": R, "train_recall": recall_train(An, B, H, tid, a.K, 4096)}), flush=True)


@torch.no_grad()
def ksweep(a, work: Path):
    """recall of the exact full-vocab top-1 / top-20 in the low-rank top-K, K in --ks, on a subsample of e0x chain states"""
    W16 = wfull(work)
    A, B = torch.load(work / a.ab)
    hs = []
    for f in sorted((work / "hn_eval").glob("*.npz")):
        z = np.load(f)["hn"]                                      # [Kd, N, d]
        hs.append(z[:4, ::a.stride].reshape(-1, z.shape[-1]))
    H = torch.from_numpy(np.concatenate(hs).astype(np.float32))
    t0 = time.time()
    ti, _, _ = exact_top(W16, H, 20)                              # [n, 20] (sorted desc)
    zt = (H @ B.T) @ A.T
    ks = [int(k) for k in a.ks.split(",")]
    order = zt.topk(max(ks), -1).indices
    rep = {"n": H.shape[0], "s": round(time.time() - t0, 1)}
    for k in ks:
        C = order[:, :k]
        inC = (ti[:, :, None] == C[:, None, :]).any(-1)
        rep[k] = {"top1": round(float(inC[:, 0].float().mean()), 5), "top5_all": round(float(inC[:, :5].all(-1).float().mean()), 5),
                  "top20_all": round(float(inC.all(-1).float().mean()), 5), "top20_frac": round(float(inC.float().mean()), 5)}
    print(json.dumps({"ksweep": a.ab, **rep}), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("phase")
    ap.add_argument("--work", default=str(Path.home() / "qwen-opt/draft-shortlist"))
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--rank", type=int, default=128)
    ap.add_argument("--K", type=int, default=128)
    ap.add_argument("--steps", type=int, default=2000)
    ap.add_argument("--bs", type=int, default=128)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--margin", type=float, default=1.0)
    ap.add_argument("--hw", type=float, default=1.0)
    ap.add_argument("--ab", default="ab_r128.pt")
    ap.add_argument("--tag", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--ks", default="128,256,512,1024,2048")
    ap.add_argument("--stride", type=int, default=8)
    ap.add_argument("--topw", type=int, default=32)
    ap.add_argument("--lams", default="1,10,100")
    ap.add_argument("--cfgs", default="ab_r128.pt:128")
    ap.add_argument("--part", default="", help="eval: i/n, only sequences with index %% n == i")
    ap.add_argument("--stats", action="store_true", help="eval: recompute every sequence (full recall stats)")
    a = ap.parse_args()
    torch.set_num_threads(a.threads)
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    {"dump-eval": dump_eval, "dump-train": dump_train, "wfull": lambda a, w: wfull(w), "targets": targets,
     "fit": fit, "eval": evaluate, "export": export, "ksweep": ksweep, "ridge": ridge}[a.phase](a, work)


if __name__ == "__main__":
    main()
