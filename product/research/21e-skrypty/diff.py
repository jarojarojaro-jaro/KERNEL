"""Weight-diff analysis between a base GGUF and its abliterated variant (CPU only).
For each selected tensor: dequantize both, D = B - A, report
  rel   = ||D||_F / ||A||_F
  e1,e4 = energy fraction of the top-1 / top-4 singular values of D (s_i^2 / ||D||_F^2)
  s1/s2
and the output-space top singular vector (rows = output dim) for cross-tensor cosine.
Usage: diff.py A.gguf B.gguf name1 name2 ...
"""
import sys, json
import numpy as np
from gguf import GGUFReader
from gguf.quants import dequantize

A = GGUFReader(sys.argv[1]); B = GGUFReader(sys.argv[2])
ta = {t.name: t for t in A.tensors}; tb = {t.name: t for t in B.tensors}
rng = np.random.default_rng(0)

def deq(t, rows=None):
    d = t.data
    if rows is not None:
        d = d[rows]
    w = dequantize(d, t.tensor_type).astype(np.float32)
    if w.ndim == 3:  # experts (n_exp, out, in) -> (out, n_exp*in): output-space rows
        return np.ascontiguousarray(w.transpose(1, 0, 2).reshape(w.shape[1], -1))
    return w.reshape(d.shape[0], -1)

def topsv(D, r=8, it=6):
    # randomized subspace iteration, D: (m, n)
    Q = np.linalg.qr(D @ rng.standard_normal((D.shape[1], r)).astype(np.float32))[0]
    for _ in range(it):
        Q = np.linalg.qr(D @ (D.T @ Q))[0]
    U, s, Vt = np.linalg.svd(Q.T @ D, full_matrices=False)
    return s, (Q @ U)[:, 0], Vt[0]

vecs = {}
for name in sys.argv[3:]:
    a, b = ta[name], tb[name]
    rows = None
    if name == 'token_embd.weight':
        rows = np.sort(rng.choice(a.data.shape[0], 16384, replace=False))
    Wa, Wb = deq(a, rows), deq(b, rows)
    D = Wb - Wa
    fro2 = float((D.astype(np.float64) ** 2).sum())
    rel = np.sqrt(fro2 / float((Wa.astype(np.float64) ** 2).sum()))
    s, u, v = topsv(D)
    e = s ** 2 / fro2
    rec = dict(t=name, ta=a.tensor_type.name, tb=b.tensor_type.name, shape=list(Wa.shape),
               rel=round(float(rel), 4), e1=round(float(e[0]), 4), e4=round(float(e[:4].sum()), 4),
               s1_s2=round(float(s[0] / s[1]), 2))
    # output-space direction: rows are outputs for weight matrices; for token_embd the hidden dim is columns
    vecs[name] = v if name == 'token_embd.weight' else u
    print(json.dumps(rec), flush=True)

names = [n for n in vecs if vecs[n].shape[0] == 5120 or vecs[n].shape[0] == 2048]
dims = {}
for n in vecs:
    dims.setdefault(vecs[n].shape[0], []).append(n)
for dim, ns in dims.items():
    if len(ns) < 2: continue
    M = np.stack([vecs[n] for n in ns])
    C = np.abs(M @ M.T)
    print(f"|cos| of top output-space singular vectors, dim {dim}:")
    for i, n in enumerate(ns):
        print(f"  {n:28s} " + " ".join(f"{C[i, j]:.2f}" for j in range(len(ns))))
