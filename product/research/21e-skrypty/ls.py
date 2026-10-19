import sys, hashlib, collections
from gguf import GGUFReader
A = GGUFReader(sys.argv[1]); B = GGUFReader(sys.argv[2])

def kv(r):
    out = {}
    for f in r.fields.values():
        if f.name.startswith('tokenizer.ggml.') and f.name not in ('tokenizer.ggml.tokens','tokenizer.ggml.merges','tokenizer.ggml.token_type'):
            pass
        try:
            v = f.contents()
        except Exception:
            v = None
        out[f.name] = v
    return out
ka, kb = kv(A), kv(B)
for k in sorted(set(ka) | set(kb)):
    va, vb = ka.get(k), kb.get(k)
    if isinstance(va, list) and len(va) > 50:
        same = va == vb
        print(f"{k}: list len {len(va)} vs {len(vb) if isinstance(vb, list) else vb} same={same}")
    elif k.startswith('general.') or k == 'tokenizer.chat_template':
        if k == 'tokenizer.chat_template':
            print(f"{k}: same={va == vb} lenA={len(va or '')} lenB={len(vb or '')} md5A={hashlib.md5((va or '').encode()).hexdigest()[:8]} md5B={hashlib.md5((vb or '').encode()).hexdigest()[:8]}")
        else:
            print(f"{k}: A={str(va)[:80]!r} B={str(vb)[:80]!r}")
    elif va != vb:
        print(f"DIFF {k}: A={str(va)[:120]} B={str(vb)[:120]}")
    elif 'qwen35' in k or k.startswith('tokenizer.ggml'):
        print(f"same {k}: {str(va)[:100]}")

ta = {t.name: t for t in A.tensors}; tb = {t.name: t for t in B.tensors}
print('tensors', len(ta), len(tb), 'onlyA', sorted(set(ta) - set(tb))[:10], 'onlyB', sorted(set(tb) - set(ta))[:10])
kinds = collections.Counter()
same_bytes = collections.Counter(); tot = collections.Counter(); typepairs = collections.defaultdict(collections.Counter)
for n in ta:
    if n not in tb: continue
    a, b = ta[n], tb[n]
    kind = n.split('.', 2)[-1] if n.startswith('blk.') else n
    tot[kind] += 1
    typepairs[kind][(a.tensor_type.name, b.tensor_type.name)] += 1
    if a.tensor_type == b.tensor_type and bytes(a.data.tobytes()) == bytes(b.data.tobytes()):
        same_bytes[kind] += 1
    if list(a.shape) != list(b.shape):
        print('SHAPE DIFF', n, a.shape, b.shape)
for k in sorted(tot):
    print(f"{k:40s} n={tot[k]:3d} identical={same_bytes[k]:3d} types={dict(typepairs[k])}")
