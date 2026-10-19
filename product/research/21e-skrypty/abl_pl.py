"""Per-layer variant of abl.py for LFM-style abliteration (one direction per layer).
For each layer: r_l = top left singular vector of D for the layer's primary writer
(attn_output or shortconv.out_proj); then s and keep for every writer of that layer
(including the MoE ffn_down_exps / dense ffn_down). Usage: abl_pl.py A.gguf B.gguf n_layer
"""
import sys, json
import numpy as np
from gguf import GGUFReader
from gguf.quants import dequantize

A = GGUFReader(sys.argv[1]); B = GGUFReader(sys.argv[2]); NL = int(sys.argv[3])
ta = {t.name: t for t in A.tensors}; tb = {t.name: t for t in B.tensors}

def deq(t):
    w = dequantize(t.data, t.tensor_type).astype(np.float64)
    if w.ndim == 3:
        return w.transpose(1, 0, 2).reshape(w.shape[1], -1)
    return w.reshape(t.data.shape[0], -1)

R = {}
for l in range(NL):
    prim = next(n for n in (f'blk.{l}.attn_output.weight', f'blk.{l}.shortconv.out_proj.weight') if n in ta)
    WA, WB = deq(ta[prim]), deq(tb[prim])
    D = WB - WA
    w, U = np.linalg.eigh(D @ D.T)
    r = U[:, -1]
    R[l] = r
    e1 = float(w[-1] / w.sum())
    row = dict(layer=l, e1=round(e1, 3))
    for n in (prim, f'blk.{l}.ffn_down.weight', f'blk.{l}.ffn_down_exps.weight'):
        if n not in ta: continue
        if n != prim:
            WA, WB = deq(ta[n]), deq(tb[n])
        pa, pb = r @ WA, r @ WB
        s = -float((pb - pa) @ pa) / float(pa @ pa)
        row[n.split('.', 2)[2].replace('.weight', '')] = dict(s=round(s, 3), keep=round(float(np.linalg.norm(pb) / np.linalg.norm(pa)), 3))
    print(json.dumps(row), flush=True)
np.save('r_lfm.npy', np.stack([R[l] for l in range(NL)]))
M = np.stack([R[l] for l in range(NL)])
C = np.abs(M @ M.T)
print('adjacent |cos|:', ' '.join(f'{C[l, l + 1]:.2f}' for l in range(NL - 1)))
