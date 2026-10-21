import sys, json, collections
sys.path.insert(0, '/home/jaro/wt/kld-ear/gguf-py')
from gguf import GGUFReader
r = GGUFReader(sys.argv[1])
out = []
for t in r.tensors:
    out.append(dict(name=t.name, type=t.tensor_type.name, n=int(t.n_elements), bytes=int(t.n_bytes), shape=[int(x) for x in t.shape]))
json.dump(out, open(sys.argv[2], 'w'), indent=0)
agg = collections.defaultdict(lambda: [0, 0, 0])
for t in out:
    import re
    role = re.sub(r'^blk\.\d+\.', '', t['name'])
    k = (role, t['type']); agg[k][0] += 1; agg[k][1] += t['n']; agg[k][2] += t['bytes']
for (role, ty), (c, n, b) in sorted(agg.items(), key=lambda x: -x[1][2]):
    if b > 5e7: print(f"{role:28s} {ty:8s} {c:3d} {n/1e9:6.3f}G par {b/1e9:6.3f} GB {8*b/n:5.2f} bpw")
print('total GB', sum(t['bytes'] for t in out)/1e9)
