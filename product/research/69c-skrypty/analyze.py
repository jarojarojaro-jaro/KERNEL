"""Astra-Stop vs our Qwen3.8-27B-Uncensored Q4_K_M GGUF (CPU only, read-only).
Checks: (1) cos(u, output.weight row of </think>) and other rows, raw and with output_norm gain;
(2) cos(u, r_qwen) = overlap with the Uncensored ablation direction; (3) ||u^T W|| and the relative
edit size on blk.63.ffn_down as served (Q6_K); (4) Q6_K survival of the edit via ggml's own quantiser
(libggml-base from the deployed engine, ctypes, no build) -> projection ratio and off-u error.
Usage: analyze.py GGUF [libggml-base.so]
"""
import sys, ctypes, json, os
import numpy as np
from gguf import GGUFReader
from gguf.quants import dequantize
from gguf.constants import GGMLQuantizationType as Q

g = GGUFReader(sys.argv[1])
T = {t.name: t for t in g.tensors}
u = np.load('u.npy').astype(np.float64); u /= np.linalg.norm(u)
out = {}

toks = g.fields['tokenizer.ggml.tokens']
names = [bytes(toks.parts[i]).decode('utf-8', 'replace') for i in toks.data]
ids = {s: names.index(s) for s in ['</think>', '<think>', '<|im_end|>', '<|endoftext|>', '\n\n', 'Wait', 'Ċ', 'ĊĊ'] if s in names}
ow = T['output.weight']
gain = dequantize(T['output_norm.weight'].data, T['output_norm.weight'].tensor_type).astype(np.float64).ravel()
def row(i):
    return dequantize(ow.data[i:i+1], ow.tensor_type).astype(np.float64).ravel()
def cos(a, b):
    return float(a @ b / np.linalg.norm(a) / np.linalg.norm(b))
out['token_ids'] = ids
out['cos_u_row'] = {s: {'raw': cos(u, row(i)), 'with_norm_gain': cos(u, row(i) * gain)} for s, i in ids.items()}
rng = np.random.default_rng(0)
rr = [abs(cos(u, row(int(i)))) for i in rng.choice(ow.data.shape[0], 512, replace=False)]
out['cos_u_random_rows'] = {'mean_abs': float(np.mean(rr)), 'max_abs': float(np.max(rr)), 'n': 512}
th = row(ids['</think>'])
out['norm_think_row'] = float(np.linalg.norm(th))

r = np.load(os.path.expanduser(os.environ.get('R_QWEN', '~/KERNEL/product/research/21e-skrypty/r_qwen.npy'))).astype(np.float64).ravel(); r /= np.linalg.norm(r)
out['cos_u_r_uncensored'] = cos(u, r)
out['cos_think_row_r_uncensored'] = cos(th, r)

t = T['blk.63.ffn_down.weight']
W = dequantize(t.data, t.tensor_type).astype(np.float64)  # (5120, 17408): rows = output (hidden) dim
out['ffn_down_63'] = {'type': t.tensor_type.name, 'shape': list(W.shape), 'bytes': int(t.n_bytes)}
v = u @ W
D = np.outer(u, v)
out['ffn_down_63'].update({'norm_uTW': float(np.linalg.norm(v)), 'norm_W': float(np.linalg.norm(W)),
                           'rel_edit': float(np.linalg.norm(D) / np.linalg.norm(W)),
                           'norm_rTW': float(np.linalg.norm(r @ W))})
W2 = W + D  # alpha = -1: W' = W - alpha*u(u^T W)

if len(sys.argv) > 2:
    lib = ctypes.CDLL(sys.argv[2])
    lib.ggml_quantize_chunk.restype = ctypes.c_size_t
    lib.ggml_quantize_chunk.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64, ctypes.c_int64, ctypes.c_int64, ctypes.c_void_p]
    def quant(M):
        src = np.ascontiguousarray(M, dtype=np.float32)
        dst = np.empty(t.n_bytes, dtype=np.uint8)
        n = lib.ggml_quantize_chunk(int(Q.Q6_K), src.ctypes.data, dst.ctypes.data, 0, M.shape[0], M.shape[1], None)
        assert n == t.n_bytes, (n, t.n_bytes)
        return dst.reshape(t.data.shape)
    # sanity: re-quantising the served (already Q6_K) tensor without edit
    q0 = quant(W)
    out['requant_noop_bytes_identical_frac'] = float(np.mean(q0 == np.asarray(t.data)))
    W0q = dequantize(q0, Q.Q6_K).astype(np.float64)
    q2 = quant(W2)
    W2q = dequantize(q2, Q.Q6_K).astype(np.float64)
    Dq = W2q - W
    out['splice'] = {
        'norm_uTW2q_over_uTW': float(np.linalg.norm(u @ W2q) / np.linalg.norm(v)),
        'rel_offu_error': float(np.linalg.norm(Dq - np.outer(u, u @ Dq)) / np.linalg.norm(W)),
        'rel_noop_requant_error': float(np.linalg.norm(W0q - W) / np.linalg.norm(W)),
        'frac_elems_changed': float(np.mean(W2q != W)),
    }
    np.save('v_uTW_blk63_unc.npy', v.astype(np.float32))
    q2.tofile('blk63_ffn_down_astra_unc.q6k')
    out['splice']['data_offset_in_file'] = int(t.data_offset)
print(json.dumps(out, indent=1))
