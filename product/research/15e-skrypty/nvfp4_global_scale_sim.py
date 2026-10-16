#!/usr/bin/env python3
"""CPU-offline: does the missing per-tensor global scale in ggml's NVFP4 quantizer
(quantize_row_nvfp4_ref: d = UE4M3(amax/6), no tensor scale, imatrix ignored) cost accuracy?
Range-reads the first ROWS rows of real Qwen3.8-27B BF16 tensors and compares weight rel-MSE of:
  A) ggml reference (as in ggml-quants.c:384-417 / ggml-impl.h:529-565)
  B) same + per-tensor FP32 global scale g = amax_tensor/(6*448) (ModelOpt-style weight_scale_2)
  C) unquantized float block scale (upper bound of what scale precision can buy)
  Q4_0-like (fp16 scale per 32, symmetric 4-bit) for reference at the same 4.5 bpw."""
import json, struct, subprocess, sys
import numpy as np
REPO = 'Qwen/Qwen3.8-27B'; ROWS = int(sys.argv[1]) if len(sys.argv) > 1 else 1024
E2M1 = np.array([0, .5, 1, 1.5, 2, 3, 4, 6], np.float32)
GRID = np.concatenate([E2M1, -E2M1[1:]])

def rr(u, a, b): return subprocess.run(['curl', '-sL', '-r', f'{a}-{b}', u], capture_output=True).stdout
wm = json.loads(subprocess.run(['curl', '-sL', f'https://huggingface.co/{REPO}/resolve/main/model.safetensors.index.json'], capture_output=True).stdout)['weight_map']

def load(t):
    u = f'https://huggingface.co/{REPO}/resolve/main/{wm[t]}'
    n = struct.unpack('<Q', rr(u, 0, 7))[0]; h = json.loads(rr(u, 8, 8 + n - 1))[t]
    rows, cols = h['shape']; r = min(ROWS, rows)
    s = 8 + n + h['data_offsets'][0]
    raw = np.frombuffer(rr(u, s, s + r * cols * 2 - 1), np.uint16).astype(np.uint32) << 16
    return raw.view(np.float32).reshape(r, cols), (rows, cols)

def ue4m3_round(x):  # ggml_fp32_to_ue4m3 followed by decode (true value, not the *0.5 convention)
    x = np.minimum(np.maximum(x, 0), 448.0)
    out = np.zeros_like(x)
    sub = x < 2.0 ** -6
    m = np.clip(np.floor(x[sub] * 512 + 0.5), 0, 7); out[sub] = m / 512
    xn = x[~sub]; e = np.floor(np.log2(xn)); mant = xn / 2 ** e  # in [1,2)
    q = np.floor((mant - 1) * 8 + 0.5) / 8 + 1  # round-half-up on 3 mantissa bits (ggml uses round bit)
    out[~sub] = q * 2 ** e
    return out

def fp4_quant(x, d):  # nearest E2M1 grid value per element, given block scale d (broadcast)
    with np.errstate(divide='ignore', invalid='ignore'):
        y = np.where(d > 0, x / d, 0)
    idx = np.abs(y[..., None] - GRID).argmin(-1)
    return GRID[idx] * d

def nvfp4(w, mode):
    b = w.reshape(-1, 16); amax = np.abs(b).max(1, keepdims=True)
    if mode == 'A': d = ue4m3_round(amax / 6)
    elif mode == 'B':
        g = np.abs(w).max() / (6 * 448); d = ue4m3_round(amax / 6 / g) * g
    else: d = amax / 6
    return fp4_quant(b, d).reshape(w.shape), d

def q4_0(w):
    b = w.reshape(-1, 32); amax_i = np.abs(b).argmax(1); mx = b[np.arange(len(b)), amax_i][:, None]
    d = (mx / -8).astype(np.float16).astype(np.float32)
    with np.errstate(divide='ignore', invalid='ignore'):
        q = np.clip(np.floor(np.where(d != 0, b / d, 0) + 8.5), 0, 15)
    return ((q - 8) * d).reshape(w.shape)

tensors = sys.argv[2:] or ['model.language_model.layers.29.linear_attn.in_proj_qkv.weight',
                           'model.language_model.layers.30.self_attn.q_proj.weight',
                           'model.language_model.layers.30.mlp.up_proj.weight',
                           'model.language_model.layers.60.mlp.down_proj.weight']
for t in tensors:
    w, shape = load(t); den = float((w ** 2).mean())
    res = {}
    for m in 'ABC':
        wq, d = nvfp4(w, m); res[m] = float(((w - wq) ** 2).mean()) / den
        if m == 'A': sub = float((d < 2 ** -6).mean()); zero = float((d == 0).mean()); nd = len(np.unique(d))
    rq4 = float(((w - q4_0(w)) ** 2).mean()) / den
    print(f'{t.split("model.language_model.")[-1]:38s} {shape} rows={w.shape[0]} std={w.std():.4f} | relMSE A(ggml)={res["A"]:.4f} '
          f'B(+global)={res["B"]:.4f} C(float scale)={res["C"]:.4f} Q4_0={rq4:.4f} | A: subnormal scales {100*sub:.1f}%, zero {100*zero:.2f}%, distinct {nd}')
