"""Astra-Stop as a rank-1 GGUF LoRA for the GGUF we actually serve (CPU, seconds, ~90 KB).
W' = W + s * u (u^T W)  ->  lora_b = u (5120x1), lora_a = (u^T W_served) (1x17408), alpha = rank = 1,
so the server's per-adapter scale s IS the edit strength: s=1 -> author's x2, s=0.5 -> x1.5, s=0 -> off.
W_served = dequantised blk.63.ffn_down of the target GGUF (Uncensored and Main differ only by
quant noise here: ||u^T W|| 1.5660 vs 1.5664, cos(u, r_uncensored) = 0.014).
Usage: make_lora.py BASE.gguf OUT.gguf [u.npy|local]
  'local' rebuilds u from the GGUF itself: u = normalise(output_norm * output.weight[</think>]).
"""
import sys
import numpy as np
from gguf import GGUFReader, GGUFWriter
from gguf.quants import dequantize

base, out = sys.argv[1], sys.argv[2]
src = sys.argv[3] if len(sys.argv) > 3 else 'u.npy'
g = GGUFReader(base); T = {t.name: t for t in g.tensors}
arch = bytes(g.fields['general.architecture'].parts[-1]).decode()
if src == 'local':
    toks = g.fields['tokenizer.ggml.tokens']
    tid = [bytes(toks.parts[i]).decode('utf-8', 'replace') for i in toks.data].index('</think>')
    ow = T['output.weight']
    row = dequantize(ow.data[tid:tid + 1], ow.tensor_type).astype(np.float64).ravel()
    gain = dequantize(T['output_norm.weight'].data, T['output_norm.weight'].tensor_type).astype(np.float64).ravel()
    u = row * gain
else:
    u = np.load(src).astype(np.float64)
u /= np.linalg.norm(u)
t = T['blk.63.ffn_down.weight']
W = dequantize(t.data, t.tensor_type).astype(np.float64)        # (n_embd=5120, n_ff=17408)
a = (u @ W).astype(np.float32).reshape(1, -1)                   # ggml ne = [17408, 1]
b = u.astype(np.float32).reshape(-1, 1)                         # ggml ne = [1, 5120]
w = GGUFWriter(out, arch)
w.add_type('adapter')
w.add_string('adapter.type', 'lora')
w.add_float32('adapter.lora.alpha', 1.0)
w.add_string('general.name', 'astra-stop-rank1-blk63-ffn_down')
w.add_tensor('blk.63.ffn_down.weight.lora_a', a)
w.add_tensor('blk.63.ffn_down.weight.lora_b', b)
w.write_header_to_file(); w.write_kv_data_to_file(); w.write_tensors_to_file(); w.close()
print(out, 'arch', arch, 'u from', src, '|u^T W|', float(np.linalg.norm(a)))
