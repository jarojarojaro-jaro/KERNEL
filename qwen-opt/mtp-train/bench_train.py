"""Phase-2 sizing: fwd+bwd throughput and peak VRAM of a recursive K-step MTP training step (bf16 weights,
frozen 64k head + embedding, CE on the draft vocab) on one sequence of T tokens with random inputs."""
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from mtp_torch import MTPHead, load_gguf_weights

T = int(sys.argv[1]) if len(sys.argv) > 1 else 2048
K = int(sys.argv[2]) if len(sys.argv) > 2 else 4
dvocab = np.loadtxt(Path.home() / "models/draft/draft_vocab_qwen38.txt", dtype=np.int64, max_rows=65536)
w = load_gguf_weights(str(Path.home() / "models/Qwen3.8-27B-UD-Q4_K_XL.gguf"), dvocab)
tm = MTPHead(w, dtype=torch.bfloat16)
tm.head.requires_grad_(False)
tm.dvocab_t = torch.from_numpy(dvocab).cuda()
params = [p for p in tm.parameters() if p.requires_grad]
print("trainable params:", sum(p.numel() for p in params) / 1e6, "M")
opt = torch.optim.AdamW(params, lr=1e-6)  # bf16 states; enough for timing / memory shape
tok = torch.randint(0, 65536, (T,), device="cuda")
tok = tm.dvocab_t[tok]
h = torch.randn(T, 5120, device="cuda", dtype=torch.bfloat16)
tgt = torch.randint(0, 65536, (T, K), device="cuda")


def step():
    pos = torch.arange(T, device="cuda")
    hn, kv = tm.forward_tf(tok, h, pos)
    loss = F.cross_entropy(tm.logits(hn).float(), tgt[:, 0])
    kv_chain, hk = [], hn
    for k in range(2, K + 1):
        with torch.no_grad():
            ids = tm.logits(hk).argmax(-1)
        hk, kvk = tm.forward_chain_step(tm.dvocab_t[ids], hk, pos + k - 1, kv, kv_chain)
        kv_chain.append(kvk)
        loss = loss + 0.6 ** (k - 1) * F.cross_entropy(tm.logits(hk).float(), tgt[:, k - 1])
    loss.backward()
    opt.step()
    opt.zero_grad(set_to_none=True)


step()
torch.cuda.synchronize()
torch.cuda.reset_peak_memory_stats()
n = 5
t0 = time.time()
for _ in range(n):
    step()
torch.cuda.synchronize()
dt = (time.time() - t0) / n
print(f"T={T} K={K}: {dt * 1e3:.0f} ms/step, {T / dt:.0f} tokens/s, peak VRAM {torch.cuda.max_memory_allocated() / 2**30:.1f} GiB")
