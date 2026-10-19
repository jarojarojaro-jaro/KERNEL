"""Estimate the refusal direction r and per-tensor abliteration scale between base A and abliterated B.
Model: W_B = W_A - s * r r^T W_A + quant noise   (rows of W = residual/output dim)
  s     = -(r^T D)(r^T W_A)^T / ||r^T W_A||^2   (1.0 = full orthogonalisation, 0 = untouched)
  keep  = ||r^T W_B|| / ||r^T W_A||              (~|1-s| plus quant floor)
  resid = energy fraction of D left after removing its r-row component (1 - ||r^T D||^2/||D||^2)
r: top right singular vector of the token_embd diff (16k sampled rows), refined by
averaging r^T-aligned top output vectors is not needed if s is consistent.
Usage: abl.py A.gguf B.gguf hidden_dim  (writes r to r.npy)
"""
import sys, json, re
import numpy as np
from gguf import GGUFReader
from gguf.quants import dequantize

A = GGUFReader(sys.argv[1]); B = GGUFReader(sys.argv[2]); H = int(sys.argv[3])
ta = {t.name: t for t in A.tensors}; tb = {t.name: t for t in B.tensors}
rng = np.random.default_rng(0)

def deq(t, rows=None):
    d = t.data if rows is None else t.data[rows]
    w = dequantize(d, t.tensor_type).astype(np.float32)
    if w.ndim == 3:
        return np.ascontiguousarray(w.transpose(1, 0, 2).reshape(w.shape[1], -1))
    return w.reshape(d.shape[0], -1)

SAMPLE = {3, 7, 15, 31, 47, 62, 63, 64}
def writers():
    pat = re.compile(r'blk\.(\d+)\.(attn_output|ssm_out|ffn_down|ffn_down_exps|shortconv\.out_proj)\.weight$')
    out = [n for n in ta if pat.match(n) and int(n.split('.')[1]) in SAMPLE]
    return sorted(out, key=lambda n: (int(n.split('.')[1]), n))

# r from embedding diff: E_B = E_A (I - s r r^T)  -> D = -s (E_A r) r^T, rank-1 with right vector r
rows = np.sort(rng.choice(ta['token_embd.weight'].data.shape[0], 16384, replace=False))
EA, EB = deq(ta['token_embd.weight'], rows), deq(tb['token_embd.weight'], rows)
D = (EB - EA).astype(np.float64)
w, V = np.linalg.eigh(D.T @ D)
r = V[:, -1]
np.save('r.npy', r)
def stats(name, WA, WB, side):
    if side == 'right':  # embedding: rows are tokens, columns hidden
        pa, pb = WA @ r, WB @ r
    else:
        pa, pb = r @ WA, r @ WB
    Dm = WB - WA
    pd = pb - pa
    s = -float(pd @ pa) / float(pa @ pa)
    keep = float(np.linalg.norm(pb) / np.linalg.norm(pa))
    resid = 1 - float(pd @ pd) / float((Dm.astype(np.float64) ** 2).sum())
    print(json.dumps(dict(t=name, ta=ta[name].tensor_type.name, tb=tb[name].tensor_type.name,
                          s=round(s, 3), keep=round(keep, 3), resid=round(resid, 3))), flush=True)

stats('token_embd.weight', EA, EB, 'right')
del EA, EB, D
for n in writers():
    if ta[n].data.shape[0] != H and not (ta[n].data.ndim == 3 and ta[n].data.shape[1] == H):
        continue
    stats(n, deq(ta[n]), deq(tb[n]), 'left')
