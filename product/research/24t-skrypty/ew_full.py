import sys, numpy as np, importlib.util
spec = importlib.util.spec_from_file_location('ce', '/home/jaro/KERNEL/product/research/24t-skrypty/code_entropy.py')
sys_argv = sys.argv; sys.argv = ['x', 'x']; ce = importlib.util.module_from_spec(spec); spec.loader.exec_module(ce); sys.argv = sys_argv
from gguf import GGUFReader
path, name = sys.argv[1], sys.argv[2]
r = GGUFReader(path); mm = np.memmap(path, np.uint8, 'r')
t = next(t for t in r.tensors if t.name == name); tn = t.tensor_type.name; bs, qk = ce.LAY[tn]; A = 1 << ce.BITS[tn]
ncol = int(t.shape[0]); rows = int(t.n_bytes) // (ncol // qk * bs); bpr = ncol // qk
j0 = np.zeros(A, np.int64); jsc = np.zeros(256 * A, np.int64); jp = np.zeros(A * A, np.int64); jr = np.zeros(A * A, np.int64)
CH = 2048
for s in range(0, rows, CH):
    n = min(CH, rows - s)
    raw = np.asarray(mm[t.data_offset + s * bpr * bs: t.data_offset + (s + n) * bpr * bs]).reshape(-1, bs)
    c, sc, *_ = ce.unpack(tn, raw); M = c.reshape(n, ncol).astype(np.int64)
    j0 += np.bincount(M.ravel(), minlength=A); jsc += np.bincount(sc.reshape(-1).astype(np.int64) * A + M.ravel(), minlength=256 * A)
    jp += np.bincount((M[:, :-1] * A + M[:, 1:]).ravel(), minlength=A * A); jr += np.bincount((M[:-1] * A + M[1:]).ravel(), minlength=A * A)
N = j0.sum()
def Hc(j):  # H(x|ctx) per symbol from joint table ctx*A+x
    jj = j.reshape(-1, A); return (ce.H(jj.ravel()) - ce.H(jj.sum(1))) / jj.sum()
print(f'{name} {tn} FULL rows={rows}: H0 {ce.H(j0)/N:.3f} Hsc {Hc(jsc):.3f} Hprev {Hc(jp):.3f} Hrow {Hc(jr):.3f} of {ce.BITS[tn]}')
