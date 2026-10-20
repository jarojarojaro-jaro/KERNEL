#!/usr/bin/env python3
"""CPU-only oracle: how much can lossless entropy coding of GGUF quant CODES save per decoded token?
(Scales were measured earlier by 15e-skrypty/scale_entropy.py: <= 2.19% of file.)

Per tensor (sampled: a few contiguous row chunks, ~SAMPLE values) it unpacks the integer quant codes
(Q4_K 4b, Q5_K 5b, Q6_K 6b, IQ4_XS/IQ4_NL 4b index, Q8_0 8b), verifies the unpack by re-packing to the
exact original bytes, and measures:
  H0        order-0 entropy, one table per tensor
  Hsc       H(code | sub-block scale)          (table per scale value)
  Hprev     H(code | previous code in row)      (order-1)
  Hrow      H(code | same column, previous row)
  Hrowtab   per-row order-0 tables (lower bound, table cost ignored)
  huf       static Huffman, one table per tensor (actual code lengths)
  slot      GPU-friendly fixed-slot Huffman: each 256-value block gets a fixed slot of S bytes (per tensor
            optimum), blocks that don't fit are escaped raw to a side array (+4 B pointer); no index.
  rans16    per-block rANS bound: H0 + 32 bits state flush per (block, interleaved stream) with 1 stream/block
and per-type zstd -3/-19 on raw block bytes (sample) as a reference.
Bytes per token: every tensor read once per token, except token_embd (get_rows) unless the output is tied;
MoE expert tensors weighted by n_used/n_expert.
Usage: code_entropy.py model.gguf [sample_values_per_tensor]
"""
import sys, re, math, heapq, subprocess, collections
import numpy as np
from gguf import GGUFReader

SAMPLE = int(sys.argv[2]) if len(sys.argv) > 2 else 1 << 21
# type -> (block bytes, values per block)
LAY = {'Q4_K': (144, 256), 'Q5_K': (176, 256), 'Q6_K': (210, 256), 'IQ4_XS': (136, 256),
       'IQ4_NL': (18, 32), 'Q8_0': (34, 32)}
BITS = {'Q4_K': 4, 'Q5_K': 5, 'Q6_K': 6, 'IQ4_XS': 4, 'IQ4_NL': 4, 'Q8_0': 8}


def k_scales(q):
    sc = np.empty(q.shape[:-1] + (8,), np.uint8)
    for j in range(4):
        sc[..., j] = q[..., j] & 63
    for j in range(4, 8):
        sc[..., j] = (q[..., j + 4] & 0xF) | ((q[..., j - 4] >> 6) << 4)
    return sc


def unpack(tn, raw):
    """raw (nb, bs) uint8 -> codes (nb, qk) uint8 in value order, ctx (nb, qk) sub-block scale, repack fn"""
    nb = raw.shape[0]
    if tn == 'Q4_K':
        qs = raw[:, 16:144].reshape(nb, 4, 32)
        c = np.stack([qs & 0xF, qs >> 4], 2).reshape(nb, 256)
        sc = np.repeat(k_scales(raw[:, 4:16]), 32, 1)

        def rp(c):
            c = c.reshape(nb, 4, 2, 32)
            return (c[:, :, 0] | (c[:, :, 1] << 4)).reshape(nb, 128)
        return c, sc, rp, (16, 144)
    if tn == 'Q5_K':
        qh = raw[:, 16:48]; ql = raw[:, 48:176].reshape(nb, 4, 32)
        c = np.empty((nb, 4, 2, 32), np.uint8)
        for j in range(4):
            c[:, j, 0] = (ql[:, j] & 0xF) | (((qh >> (2 * j)) & 1) << 4)
            c[:, j, 1] = (ql[:, j] >> 4) | (((qh >> (2 * j + 1)) & 1) << 4)
        sc = np.repeat(k_scales(raw[:, 4:16]), 32, 1)

        def rp(cc):
            cc = cc.reshape(nb, 4, 2, 32)
            qh = np.zeros((nb, 32), np.uint8)
            for j in range(4):
                qh |= ((cc[:, j, 0] >> 4) & 1) << (2 * j)
                qh |= ((cc[:, j, 1] >> 4) & 1) << (2 * j + 1)
            ql = ((cc[:, :, 0] & 0xF) | ((cc[:, :, 1] & 0xF) << 4)).reshape(nb, 128)
            return np.concatenate([qh, ql], 1)
        return c.reshape(nb, 256), sc, rp, (16, 176)
    if tn == 'Q6_K':
        ql = raw[:, 0:128].reshape(nb, 2, 64); qh = raw[:, 128:192].reshape(nb, 2, 32)
        c = np.empty((nb, 2, 4, 32), np.uint8)
        c[:, :, 0] = (ql[:, :, :32] & 0xF) | ((qh & 3) << 4)
        c[:, :, 1] = (ql[:, :, 32:] & 0xF) | (((qh >> 2) & 3) << 4)
        c[:, :, 2] = (ql[:, :, :32] >> 4) | (((qh >> 4) & 3) << 4)
        c[:, :, 3] = (ql[:, :, 32:] >> 4) | (((qh >> 6) & 3) << 4)
        sc = np.repeat(raw[:, 192:208], 16, 1)

        def rp(cc):
            cc = cc.reshape(nb, 2, 4, 32)
            lo = np.concatenate([(cc[:, :, 0] & 0xF) | ((cc[:, :, 2] & 0xF) << 4),
                                 (cc[:, :, 1] & 0xF) | ((cc[:, :, 3] & 0xF) << 4)], 2)
            hi = (cc[:, :, 0] >> 4) | ((cc[:, :, 1] >> 4) << 2) | ((cc[:, :, 2] >> 4) << 4) | ((cc[:, :, 3] >> 4) << 6)
            return np.concatenate([lo.reshape(nb, 128), hi.reshape(nb, 64)], 1)
        return c.reshape(nb, 256), sc, rp, (0, 192)
    if tn == 'IQ4_XS':
        qs = raw[:, 8:136].reshape(nb, 8, 16)
        c = np.stack([qs & 0xF, qs >> 4], 2).reshape(nb, 256)
        sh = raw[:, 2].astype(np.uint16) | (raw[:, 3].astype(np.uint16) << 8)
        ls = np.empty((nb, 8), np.uint8)
        for ib in range(8):
            ls[:, ib] = ((raw[:, 4 + ib // 2] >> (4 * (ib % 2))) & 0xF) | (((sh >> (2 * ib)) & 3) << 4).astype(np.uint8)

        def rp(cc):
            cc = cc.reshape(nb, 8, 2, 16)
            return (cc[:, :, 0] | (cc[:, :, 1] << 4)).reshape(nb, 128)
        return c, np.repeat(ls, 32, 1), rp, (8, 136)
    if tn == 'IQ4_NL':
        qs = raw[:, 2:18]
        c = np.concatenate([qs & 0xF, qs >> 4], 1)
        return c, np.zeros_like(c), (lambda cc: cc[:, :16] | (cc[:, 16:] << 4)), (2, 18)
    if tn == 'Q8_0':
        c = raw[:, 2:34] ^ 0x80  # int8 -> offset binary
        return c, np.zeros_like(c), (lambda cc: cc ^ 0x80), (2, 34)
    raise KeyError(tn)


def H(counts):
    c = counts[counts > 0].astype(np.float64); n = c.sum()
    return float(-(c * np.log2(c / n)).sum())  # total bits


def Hcond(ctx, x, A):
    j = np.bincount(ctx.astype(np.int64) * A + x, minlength=0)
    m = np.bincount(ctx.astype(np.int64))
    return H(j) - H(m)


def huff_lengths(counts):
    sy = [(int(c), i) for i, c in enumerate(counts) if c > 0]
    L = np.zeros(len(counts), np.int64)
    if len(sy) == 1:
        L[sy[0][1]] = 1; return L
    h = [(c, k, [i]) for k, (c, i) in enumerate(sy)]
    heapq.heapify(h); k = len(h)
    while len(h) > 1:
        a = heapq.heappop(h); b = heapq.heappop(h)
        for i in a[2] + b[2]:
            L[i] += 1
        heapq.heappush(h, (a[0] + b[0], k, a[2] + b[2])); k += 1
    return L


def main(path):
    r = GGUFReader(path)
    kv = {}
    for k, f in r.fields.items():
        try:
            kv[k] = f.parts[f.data[0]].tolist()
        except Exception:
            pass
    arch = kv.get('general.architecture', [b''])
    arch = bytes(arch).decode() if isinstance(arch, list) else str(arch)
    n_exp = next((v[0] for k, v in kv.items() if k.endswith('.expert_count')), 0)
    n_used = next((v[0] for k, v in kv.items() if k.endswith('.expert_used_count')), 0)
    names = {t.name for t in r.tensors}
    tied = 'output.weight' not in names
    print(f'# {path}\n# arch={arch} experts {n_used}/{n_exp} tied_output={tied} sample={SAMPLE}')
    mm = np.memmap(path, dtype=np.uint8, mode='r')
    T = collections.defaultdict(lambda: collections.defaultdict(float))
    zs = collections.defaultdict(list)
    tot_read = 0.0; other_read = 0.0
    for t in r.tensors:
        tn = t.tensor_type.name
        w = 1.0
        if t.name == 'token_embd.weight' and not tied:
            w = 0.0
        if '_exps' in t.name and n_exp:
            w = n_used / n_exp
        nbytes = int(t.n_bytes)
        tot_read += w * nbytes
        if tn not in LAY or w == 0.0:
            other_read += w * nbytes
            continue
        bs, qk = LAY[tn]
        ncol = int(t.shape[0]); rows = int(np.prod([int(x) for x in t.shape[1:]]))
        bpr = ncol // qk
        allb = mm[t.data_offset: t.data_offset + nbytes]
        assert allb.size == rows * bpr * bs
        want_rows = max(2, SAMPLE // ncol)
        # 8 chunks centred in equal row strata: the last rows of LFM token_embd (ids >= ~125k) are
        # near-identical reserved tokens and badly bias a tail-anchored sample (full tensor Hrow 5.74 vs 4.42)
        nch = 8; per = max(2, min(rows, want_rows) // nch)
        starts = sorted(set(min(rows - per, max(0, int((i + 0.5) * rows / nch) - per // 2)) for i in range(nch)))
        a = T[tn]
        a['bytes_read'] += w * nbytes
        acc = collections.defaultdict(float)
        for s in starts:
            raw = np.asarray(allb[s * bpr * bs:(s + per) * bpr * bs]).reshape(per * bpr, bs)
            c, sc, rp, (q0, q1) = unpack(tn, raw)
            assert np.array_equal(rp(c), raw[:, q0:q1]), f'repack mismatch {t.name}'
            A = 1 << BITS[tn]
            x = c.reshape(-1).astype(np.int64)
            n = x.size
            cnt = np.bincount(x, minlength=A)
            acc['n'] += n
            acc['cnt'] = acc.get('cnt', 0) + cnt  # type: ignore
            acc['Hsc'] += Hcond(sc.reshape(-1), x, A)
            M = c.reshape(per, ncol).astype(np.int64)
            acc['Hprev'] += Hcond(M[:, :-1].reshape(-1), M[:, 1:].reshape(-1), A) + H(np.bincount(M[:, 0], minlength=A))
            acc['Hrow'] += Hcond(M[:-1].reshape(-1), M[1:].reshape(-1), A) + H(np.bincount(M[0], minlength=A))
            acc['Hrowtab'] += sum(H(np.bincount(M[i], minlength=A)) for i in range(per))
            acc['qbytes'] += raw.shape[0] * (q1 - q0); acc['bytes'] += raw.size
            acc.setdefault('blocks', []).append(c)  # type: ignore
            if len(zs[tn]) < 6:
                zs[tn].append(raw.tobytes()[: 4 << 20])
        cnt = acc['cnt']; n = acc['n']
        h0 = H(cnt)
        L = huff_lengths(cnt)
        huf = float((cnt * L).sum())
        # per-block Huffman size distribution -> fixed slot with escapes (GPU-friendly, no index)
        cb = np.concatenate(acc['blocks'])  # (nb, qk)
        bb = L[cb.astype(np.int64)].sum(1)  # bits per block
        rawq = (acc['qbytes'] / cb.shape[0])  # code bytes per block
        best = (rawq, 0.0)
        for S in range(int(rawq * 0.5), int(rawq) + 1):
            esc = float((bb > 8 * S).mean())
            cost = S + esc * (rawq + 4)
            if cost < best[0]:
                best = (cost, esc)
        frac = acc['qbytes'] / acc['bytes']  # code fraction of tensor bytes
        bitsq = BITS[tn] * n
        for k, v in (('H0', h0), ('Hsc', acc['Hsc']), ('Hprev', acc['Hprev']), ('Hrow', acc['Hrow']),
                     ('Hrowtab', acc['Hrowtab']), ('huf', huf)):
            rel = v / bitsq  # compressed / raw code bits
            a[k] += w * nbytes * frac * (1 - rel)  # bytes saved per token
        a['slot'] += w * nbytes * frac * (1 - best[0] / rawq)
        a['rans'] += w * nbytes * frac * (1 - min(1.0, (h0 / n * qk + 32) / (BITS[tn] * qk)))
        a['qfrac_read'] += w * nbytes * frac
        a['h0bits'] += w * nbytes * frac * (h0 / n) / BITS[tn]
        a['esc'] += w * nbytes * best[1]
        print(f'{t.name:40s} {tn:6s} w={w:.3f} {nbytes/1e6:8.1f}MB H0 {h0/n:.3f}/{BITS[tn]} Hsc {acc["Hsc"]/n:.3f} '
              f'Hprev {acc["Hprev"]/n:.3f} Hrow {acc["Hrow"]/n:.3f} Hrowtab {acc["Hrowtab"]/n:.3f} huf {huf/n:.3f} '
              f'slot {8*best[0]/qk:.3f}b esc {100*best[1]:.1f}%', flush=True)
    print('\n# per type: bytes read per token (GB) and % of ALL bytes read per token saved by each model')
    keys = ['H0', 'Hsc', 'Hprev', 'Hrow', 'Hrowtab', 'huf', 'slot', 'rans']
    print(f'{"type":7s} {"GB/tok":>7s} {"code%":>6s} {"H0/b":>6s} ' + ' '.join(f'{k:>7s}' for k in keys))
    tots = collections.defaultdict(float)
    for tn, a in sorted(T.items(), key=lambda kv: -kv[1]['bytes_read']):
        br = a['bytes_read']
        print(f'{tn:7s} {br/1e9:7.3f} {100*a["qfrac_read"]/br:6.1f} {a["h0bits"]/a["qfrac_read"]:6.3f} '
              + ' '.join(f'{100*a[k]/br:6.2f}%' for k in keys))
        for k in keys:
            tots[k] += a[k]
    print(f'{"ALL":7s} {tot_read/1e9:7.3f} (other/unanalysed {other_read/1e9:.3f} GB) '
          + ' '.join(f'{100*tots[k]/tot_read:6.2f}%' for k in keys))
    print('# saved GB/token: ' + ' '.join(f'{k}={tots[k]/1e9:.3f}' for k in keys))
    print('\n# zstd on raw block bytes (sample <=24 MB/type); ratio = compressed/raw')
    for tn, chunks in zs.items():
        buf = b''.join(chunks)
        out = []
        for lvl in ('-3', '-19'):
            p = subprocess.run(['zstd', lvl, '-T1', '-c'], input=buf, capture_output=True, check=True)
            out.append(f'zstd{lvl} {len(p.stdout)/len(buf):.4f}')
        print(f'{tn:7s} {len(buf)/1e6:6.1f} MB ' + ' '.join(out))


if __name__ == '__main__':
    main(sys.argv[1])
