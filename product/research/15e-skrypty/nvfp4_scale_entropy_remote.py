#!/usr/bin/env python3
"""Range-read a sample of NVFP4 blocks from a remote GGUF and measure how compressible the
UE4M3 sub-block scales are: order-0/1 entropy and a CSF-like 'byte-window4 + exceptions' code
(per-row base byte, 4-bit offset per scale, 4-byte exception record when offset not in [0,15])."""
import sys, subprocess, collections
import numpy as np
sys.path.insert(0, __import__('os').path.dirname(__file__))
import ggufhead as gh
from scale_entropy import H0, H1

url = sys.argv[1]; rows_per_tensor = int(sys.argv[2]) if len(sys.argv) > 2 else 64
b = gh.Buf(url)
assert b.read(4) == b'GGUF'
ver = b.u32(); nt = b.u64(); nkv = b.u64()
kv = {}
for _ in range(nkv):
    k = b.s(); t = b.u32(); kv[k] = gh.val(b, t)
tens = []
for _ in range(nt):
    name = b.s(); nd = b.u32(); dims = [b.u64() for _ in range(nd)]; t = b.u32(); off = b.u64()
    tens.append((name, dims, t, off))
ds = (b.pos + 31) // 32 * 32
nv = [x for x in tens if x[2] == 40]
print('NVFP4 tensors', len(nv))
pick = [x for x in nv if x[0].startswith(('blk.5.', 'blk.30.', 'blk.60.'))]
tot = collections.Counter()
for name, dims, t, off in pick:
    bpr = dims[0] // 64; nbytes = rows_per_tensor * bpr * 36
    raw = subprocess.run(['curl', '-sL', '-r', f'{ds+off}-{ds+off+nbytes-1}', url], capture_output=True).stdout
    blk = np.frombuffer(raw, np.uint8).reshape(rows_per_tensor, bpr, 36)
    sc = blk[:, :, 0:4].reshape(rows_per_tensor, bpr * 4)  # scales of one row, in order
    flat = sc.reshape(-1)
    h0 = H0(flat); h1 = H1(flat[:-1], flat[1:])
    # CSF-like: choose per-row base minimizing exceptions over windows [base, base+15]
    exc = 0
    for r in range(rows_per_tensor):
        v = sc[r].astype(np.int32)
        hist = np.bincount(v, minlength=256)
        win = np.convolve(hist, np.ones(16, int), 'full')[15:15 + 241]  # count in [base, base+15]
        exc += v.size - int(win.max())
    n = flat.size
    csf_bits = n * 4 + rows_per_tensor * 8 + exc * 32
    tot['n'] += n; tot['h0'] += n * h0; tot['h1'] += n * min(h0, h1); tot['csf'] += csf_bits; tot['exc'] += exc
    print(f'{name:28s} {dims} H0={h0:.2f} H1={h1:.2f} bits/scale; exceptions={100*exc/n:.2f}%; csf={csf_bits/n:.2f} bits/scale')
n = tot['n']
print(f'TOTAL scales={n}: raw 8.00, H0 {tot["h0"]/n:.2f}, H1 {tot["h1"]/n:.2f}, CSF-like {tot["csf"]/n:.2f} bits/scale; exceptions {100*tot["exc"]/n:.2f}%')
for lbl, bits in (('H1', tot['h1'] / n), ('CSF', tot['csf'] / n)):
    bpw = 4 + bits / 16
    print(f'  {lbl}: NVFP4 bpw 4.50 -> {bpw:.3f}  (bytes -{100*(4.5-bpw)/4.5:.1f}% on NVFP4 tensors)')
