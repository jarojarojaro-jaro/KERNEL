#!/usr/bin/env python3
"""Ternary Bonsai 2.5 27B Uncensored (AtomicChat PTQ1_0) + prism MTP head -> PTQ1_0-mtp and lossless Q2_0-mtp.
usage: build_b25.py UNC.gguf MTP_HEADER.bin MTP64.bin MTP_DATA_START OUT_PTQ1-mtp.gguf [OUT_Q2-mtp.gguf]
PTQ1_0 (prism type 143, 128 trits + fp16 d) -> Q2_0 (type 42, 2x 64 x 2-bit, same d): code q = trit, (q-1)*d both sides."""
import sys, numpy as np, gguf_min as g
unc_p, mh_p, m64_p, mds, out1 = sys.argv[1:6]; out2 = sys.argv[6] if len(sys.argv) > 6 else None
mds = int(mds)
U = g.parse(open(unc_p, 'rb').read(64 << 20)); H = g.parse(open(mh_p, 'rb').read())
ut = {t['name']: t for t in U['tensors']}
# KV: everything but block_count/nextn must match the uncensored file's
uk = dict(U['kv']); hk = dict(H['kv'])
diff = [k for k in set(uk) | set(hk) if uk.get(k) != hk.get(k)]
print('KV differing (unc vs prism mtp):', diff)
assert set(diff) <= {'qwen35.block_count', 'qwen35.nextn_predict_layers', 'general.name'}, diff
m64 = open(m64_p, 'rb'); m64_base = min(t['off'] for t in H['tensors'] if t['name'].startswith('blk.64.'))
POW3 = np.array([1, 3, 9, 27, 81, 243], np.uint8)
def trits(b):   # b: (n,) uint8 -> (n,k) trits for k powers
    return lambda n: ((((b * POW3[n]).astype(np.uint8)).astype(np.uint16) * 3) >> 8).astype(np.uint8)
def ptq1_to_q2(raw):
    a = np.frombuffer(raw, np.uint8).reshape(-1, 28); nb = a.shape[0]
    qs, qh, d = a[:, :24], a[:, 24:26], a[:, 26:28]
    v = np.empty((nb, 128), np.uint8); k = 0
    for j0, c in ((0, 16), (16, 8)):
        for n in range(5):
            v[:, k:k + c] = ((((qs[:, j0:j0 + c] * POW3[n]).astype(np.uint8)).astype(np.uint16) * 3) >> 8); k += c
    for n in range(4):
        v[:, k:k + 2] = ((((qh * POW3[n]).astype(np.uint8)).astype(np.uint16) * 3) >> 8); k += 2
    assert k == 128 and v.max() <= 2
    v = v.reshape(nb * 2, 16, 4)
    packed = (v[:, :, 0] | (v[:, :, 1] << 2) | (v[:, :, 2] << 4) | (v[:, :, 3] << 6)).astype(np.uint8)
    out = np.empty((nb * 2, 18), np.uint8)
    out[:, :2] = np.repeat(d, 2, axis=0); out[:, 2:] = packed
    return out.tobytes()
def src_bytes(t, f_unc):
    if t['name'].startswith('blk.64.'):
        m64.seek(t['off'] - m64_base); return m64.read(t['nbytes'])
    u = ut[t['name']]; assert u['dims'] == t['dims'] and u['type'] == t['type'], t['name']
    f_unc.seek(U['data_start'] + u['off']); return f_unc.read(u['nbytes'])
for out, q2 in ((out1, False), (out2, True)):
    if not out: continue
    ts = [dict(t) for t in H['tensors']]
    for t in ts:
        if q2 and t['type'] == 143:
            n = 1
            for x in t['dims']: n *= x
            t['type'] = 42; t['nbytes'] = n // 64 * 18
    hdr = g.header(H['nkv'], H['kv_raw'], ts, H['align'])
    with open(unc_p, 'rb') as fu, open(out, 'wb') as fo:
        fo.write(hdr); base = len(hdr)
        for t, t0 in zip(ts, H['tensors']):
            fo.seek(base + t['off'])
            b = src_bytes(t0, fu)
            if q2 and t0['type'] == 143:
                CH = 28 * (1 << 20); b = b''.join(ptq1_to_q2(b[i:i + CH]) for i in range(0, len(b), CH))
            assert len(b) == t['nbytes'], t['name']; fo.write(b)
        fo.truncate(base + ts[-1]['off'] + ts[-1]['nbytes'])
    print('wrote', out)
