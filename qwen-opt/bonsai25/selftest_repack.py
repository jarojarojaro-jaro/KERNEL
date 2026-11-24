# self-test: PTQ1_0 encoded per prism's decode formula -> ptq1_to_q2 -> Q2_0 decode == PTQ1_0 decode, bit for bit
import numpy as np, sys
sys.argv = ['x', 'a', 'b', 'c', '0', 'e']
src = open('build_b25.py').read(); ns = {}
exec('import numpy as np\nPOW3 = ' + src.split('POW3 =')[1].split('def src_bytes')[0], ns)
rng = np.random.default_rng(0); nb = 2000
tr = rng.integers(0, 3, (nb, 128)); d = rng.standard_normal(nb).astype(np.float16)
lut5 = {}; lut4 = {}
for b in range(256):
    lut5.setdefault(tuple(((((b * p) & 255) * 3) >> 8) for p in [1, 3, 9, 27, 81]), b)
    lut4.setdefault(tuple(((((b * p) & 255) * 3) >> 8) for p in [1, 3, 9, 27]), b)
seq = [('s', j0 + m, n) for j0, c in ((0, 16), (16, 8)) for n in range(5) for m in range(c)] + [('h', h, n) for n in range(4) for h in range(2)]
raw = bytearray(); ref = []
for i in range(nb):
    cols = {}
    for idx, (w, b, n) in enumerate(seq): cols.setdefault((w, b), {})[n] = int(tr[i, idx])
    qs = [lut5[tuple(cols[('s', b)][n] for n in range(5))] for b in range(24)]
    qh = [lut4[tuple(cols[('h', b)][n] for n in range(4))] for b in range(2)]
    raw += bytes(qs) + bytes(qh) + d[i].tobytes()
    ref.append((tr[i].astype(np.float32) - 1) * np.float32(d[i]))
out = np.frombuffer(ns['ptq1_to_q2'](bytes(raw)), np.uint8).reshape(-1, 18)
dq = np.frombuffer(out[:, :2].tobytes(), np.float16).astype(np.float32)
q = np.stack([(out[:, 2:] >> s) & 3 for s in (0, 2, 4, 6)], -1).reshape(-1, 64)
y = ((q.astype(np.float32) - 1) * dq[:, None]).reshape(nb, 128)
print('blocks', nb, 'max |diff|', float(np.abs(y - np.array(ref)).max()))
