"""Q6_K/Q8_0 survival of the Astra edit when re-quantising the already-quantised served tensor.
Variants: plain, over-drive k, error feedback along u (iterate q = Q(W2 + u u^T (W2 - deq(q)))).
Usage: splice_variants.py GGUF libggml-base.so
"""
import sys, ctypes, json
import numpy as np
from gguf import GGUFReader
from gguf.quants import dequantize
from gguf.constants import GGMLQuantizationType as Q

g = GGUFReader(sys.argv[1]); t = {x.name: x for x in g.tensors}['blk.63.ffn_down.weight']
lib = ctypes.CDLL(sys.argv[2])
lib.ggml_quantize_chunk.restype = ctypes.c_size_t
lib.ggml_quantize_chunk.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64, ctypes.c_int64, ctypes.c_int64, ctypes.c_void_p]
lib.ggml_row_size.restype = ctypes.c_size_t
lib.ggml_row_size.argtypes = [ctypes.c_int, ctypes.c_int64]
u = np.load('u.npy').astype(np.float64); u /= np.linalg.norm(u)
W = dequantize(t.data, t.tensor_type).astype(np.float64)
v = u @ W; nW = np.linalg.norm(W); nv = np.linalg.norm(v)
W2 = W + np.outer(u, v)

def qd(M, typ):
    src = np.ascontiguousarray(M, dtype=np.float32)
    rs = lib.ggml_row_size(int(typ), M.shape[1])
    dst = np.empty(rs * M.shape[0], dtype=np.uint8)
    lib.ggml_quantize_chunk(int(typ), src.ctypes.data, dst.ctypes.data, 0, M.shape[0], M.shape[1], None)
    return dequantize(dst.reshape(M.shape[0], rs), typ).astype(np.float64), dst

def stats(Mq):
    Dq = Mq - W
    return {'ratio': float(np.linalg.norm(u @ Mq) / nv),
            'cos_uTWq_target': float((u @ Mq) @ (2 * v) / np.linalg.norm(u @ Mq) / np.linalg.norm(2 * v)),
            'rel_offu_err': float(np.linalg.norm(Dq - np.outer(u, u @ Dq)) / nW)}
res = {}
for k in (1.0, 1.15, 1.3):
    res[f'Q6_K k={k}'] = stats(qd(W + k * np.outer(u, v), Q.Q6_K)[0])
target = W2.copy(); X = W2.copy()
for it in range(4):
    Xq, raw = qd(X, Q.Q6_K)
    X = X + np.outer(u, u @ (target - Xq))
    res[f'Q6_K errfb it={it}'] = stats(Xq)
raw.tofile('blk63_ffn_down_astra_unc_errfb.q6k')
res['Q8_0 k=1'] = stats(qd(W2, Q.Q8_0)[0])
print(json.dumps(res, indent=1))
