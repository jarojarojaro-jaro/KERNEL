#!/usr/bin/env python3
"""CPU-offline: how compressible (losslessly) are the block-scale fields of a GGUF?
Reads tensor table from a local GGUF, then for Q4_K/Q5_K/Q6_K/IQ4_XS/NVFP4 tensors computes
order-0 entropy (per tensor) and order-1 conditional entropy (previous sub-block in the same
super-block / previous super-block in the row) of the scale fields, and the bound on bytes saved.
Usage: scale_entropy.py model.gguf [max_blocks_per_tensor]"""
import sys, struct, collections, math
import numpy as np
sys.path.insert(0, __import__('os').path.dirname(__file__))
import ggufhead as gh

def parse_local(path):
    b = gh.Buf('file://' + path)
    assert b.read(4) == b'GGUF'
    ver = b.u32(); nt = b.u64(); nkv = b.u64()
    kv = {}
    for _ in range(nkv):
        k = b.s(); t = b.u32(); kv[k] = gh.val(b, t)
    tens = []
    for _ in range(nt):
        name = b.s(); nd = b.u32(); dims = [b.u64() for _ in range(nd)]; t = b.u32(); off = b.u64()
        tens.append((name, dims, t, off))
    align = kv.get('general.alignment', 32)
    return tens, (b.pos + align - 1) // align * align

BLK = {12: ('Q4_K', 144, 256), 13: ('Q5_K', 176, 256), 14: ('Q6_K', 210, 256), 23: ('IQ4_XS', 136, 256), 40: ('NVFP4', 36, 64)}

def H0(x):
    _, c = np.unique(x, return_counts=True)
    p = c / c.sum()
    return float(-(p * np.log2(p)).sum())

def H1(prev, cur):
    # conditional entropy H(cur | prev) = H(prev,cur) - H(prev)
    joint = prev.astype(np.int64) * 65536 + cur.astype(np.int64)
    return H0(joint) - H0(prev)

def k_scales(sc12):
    q = sc12.astype(np.uint8)
    sc = np.empty(q.shape[:-1] + (8,), np.uint8); m = np.empty_like(sc)
    for j in range(4):
        sc[..., j] = q[..., j] & 63; m[..., j] = q[..., j + 4] & 63
    for j in range(4, 8):
        sc[..., j] = (q[..., j + 4] & 0xF) | ((q[..., j - 4] >> 6) << 4)
        m[..., j] = (q[..., j + 4] >> 4) | ((q[..., j] >> 6) << 4)
    return sc, m

def main(path, maxb=None):
    tens, ds = parse_local(path)
    mm = np.memmap(path, dtype=np.uint8, mode='r')
    acc = collections.defaultdict(lambda: collections.defaultdict(float))
    total_bits_file = 0.0
    for name, dims, t, off in tens:
        ne = 1
        for d in dims: ne *= d
        if t not in BLK: continue
        tn, bs, qk = BLK[t]
        nb = ne // qk
        rowb = dims[0] // qk  # blocks per row
        raw = mm[ds + off: ds + off + nb * bs].reshape(nb, bs)
        if maxb and nb > maxb:
            nrow = max(1, maxb // rowb); raw = raw[: nrow * rowb]; nb = raw.shape[0]
        a = acc[tn]; a['blocks'] += nb; a['bits'] += nb * bs * 8
        fields = {}
        if tn in ('Q4_K', 'Q5_K'):
            d = raw[:, 0:2].copy().view(np.uint16)[:, 0]; dm = raw[:, 2:4].copy().view(np.uint16)[:, 0]
            sc, m = k_scales(raw[:, 4:16])
            fields = {'d': (d, 16, 1), 'dmin': (dm, 16, 1), 'sc6': (sc, 6, 8), 'm6': (m, 6, 8)}
        elif tn == 'Q6_K':
            sc = raw[:, 192:208].copy().view(np.int8).astype(np.int16) + 128
            d = raw[:, 208:210].copy().view(np.uint16)[:, 0]
            fields = {'d': (d, 16, 1), 'sc8': (sc.astype(np.uint16), 8, 16)}
        elif tn == 'IQ4_XS':
            d = raw[:, 0:2].copy().view(np.uint16)[:, 0]
            sh = raw[:, 2:4].copy().view(np.uint16)[:, 0].astype(np.uint16)
            sl = raw[:, 4:8]
            ls = np.empty((nb, 8), np.uint8)
            for ib in range(8):
                ls[:, ib] = ((sl[:, ib // 2] >> (4 * (ib % 2))) & 0xF) | (((sh >> (2 * ib)) & 3) << 4).astype(np.uint8)
            fields = {'d': (d, 16, 1), 'sc6': (ls, 6, 8)}
        elif tn == 'NVFP4':
            sc = raw[:, 0:4]
            fields = {'e4m3': (sc, 8, 4)}
        for f, (v, bits, per) in fields.items():
            v2 = v.reshape(nb, per) if per > 1 else v.reshape(nb, 1)
            flat = v2.reshape(-1)
            h0 = H0(flat)
            # order-1 context: previous symbol in raster order (sub-block within superblock, then next superblock in row)
            h1 = H1(flat[:-1], flat[1:]) if flat.size > 1 else h0
            n = flat.size
            a[f + '.raw'] += n * bits; a[f + '.h0'] += n * h0; a[f + '.h1'] += n * min(h0, h1)
    print(f'file {path}')
    gt_bits = sum(a['bits'] for a in acc.values()); gt_save0 = gt_save1 = 0.0
    for tn, a in acc.items():
        fs = sorted({k.rsplit('.', 1)[0] for k in a if '.' in k})
        raw_scale = sum(a[f + '.raw'] for f in fs); s0 = sum(a[f + '.raw'] - a[f + '.h0'] for f in fs); s1 = sum(a[f + '.raw'] - a[f + '.h1'] for f in fs)
        gt_save0 += s0; gt_save1 += s1
        w = a['blocks'] * {'Q4_K': 256, 'Q5_K': 256, 'Q6_K': 256, 'IQ4_XS': 256, 'NVFP4': 64}[tn]
        print(f'{tn:7s} GB={a["bits"]/8e9:6.3f} scale-overhead={raw_scale/w:.4f} bpw of {a["bits"]/w:.4f}; '
              + ' '.join(f'{f}: raw {a[f+".raw"]/w:.4f} H0 {a[f+".h0"]/w:.4f} H1 {a[f+".h1"]/w:.4f}' for f in fs)
              + f' | save H0 {100*s0/a["bits"]:.2f}% H1 {100*s1/a["bits"]:.2f}% of type bytes')
    print(f'ALL analysed types: {gt_bits/8e9:.3f} GB; lossless saving bound H0 {100*gt_save0/gt_bits:.2f}%  H1 {100*gt_save1/gt_bits:.2f}%  (= {gt_save1/8e9:.3f} GB)')

if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None)
