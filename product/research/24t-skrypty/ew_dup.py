import sys, hashlib, collections, numpy as np
from gguf import GGUFReader
r = GGUFReader(sys.argv[1]); name = sys.argv[2]
t = next(t for t in r.tensors if t.name == name)
rows = int(np.prod([int(x) for x in t.shape[1:]])); rb = int(t.n_bytes) // rows
mm = np.memmap(sys.argv[1], np.uint8, 'r')
d = collections.Counter(); first = {}
for i in range(rows):
    h = hashlib.blake2b(mm[t.data_offset + i*rb: t.data_offset + (i+1)*rb].tobytes(), digest_size=16).digest()
    d[h] += 1; first.setdefault(h, i)
dup = sum(c - 1 for c in d.values())
big = sorted(((c, first[h]) for h, c in d.items() if c > 1), reverse=True)[:5]
print(f'{name} rows={rows} rowbytes={rb} unique={len(d)} duplicate_rows={dup} ({100*dup/rows:.2f}%) saved={dup*rb/1e6:.1f} MB; top groups (count, first_row) {big}')
