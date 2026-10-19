"""Zero-input GDN decay half-lives for qwen35 GGUF: decay = exp(ssm_a * softplus(ssm_dt.bias))
(qwen35.cpp:369-373). Usage: gdn_decay.py model.gguf"""
import sys
import numpy as np
from gguf import GGUFReader

t = {x.name: x for x in GGUFReader(sys.argv[1]).tensors}
hl = []
for l in range(64):
    if f'blk.{l}.ssm_a' not in t:
        continue
    a = np.array(t[f'blk.{l}.ssm_a'].data, dtype=np.float64)
    b = np.array(t[f'blk.{l}.ssm_dt.bias'].data, dtype=np.float64)
    hl.append(np.log(2) / -(a * np.log1p(np.exp(b))))
hl = np.concatenate(hl)
print('heads', hl.size)
for q in (5, 25, 50, 75, 90, 95, 99):
    print(f'p{q}', round(float(np.percentile(hl, q)), 1))
for thr in (16, 64, 256, 1024, 4096, 16384):
    print(f'frac > {thr}', round(float((hl > thr).mean()), 3))
print('max', hl.max())
