"""Draft-vocab (64k) misses: share of output tokens outside the draft vocab, and share of those present earlier in context."""
import json, pickle, sys
import numpy as np
V = np.loadtxt('/home/jaro/models/draft/draft_vocab_qwen38.txt', dtype=np.int64)[:65536]
inv = np.zeros(300000, bool); inv[V] = True
def acc(S, a, b, agg, cls):
    out = S[a:b]
    miss = ~inv[out]
    seen = np.zeros(300000, bool)
    seen[S[:a]] = True
    inctx = 0
    # walk outputs: a token is "in context" if it appeared anywhere before its position
    for t in out:
        if not inv[t] and seen[t]:
            inctx += 1
        seen[t] = True
    g = agg.setdefault(cls, [0, 0, 0]); g[0] += len(out); g[1] += int(miss.sum()); g[2] += inctx
agg = {}
for line in open('/home/jaro/qwen-opt/mtp-train/data/gen_p1.jsonl'):
    d = json.loads(line)
    S = np.asarray(d['prompt_ids'] + d['resp_ids'], dtype=np.int64)
    acc(S, len(d['prompt_ids']), len(S), agg, f"chat:{d.get('lang')}:{d.get('src') or d.get('cat')}")
if len(sys.argv) > 1:
    data = pickle.load(open('/tmp/specsim/agent_streams.pkl', 'rb'))
    rng = np.random.default_rng(1)
    for j in rng.permutation(len(data))[:int(sys.argv[1])]:
        name, S, segs = data[j]
        S = S.astype(np.int64)
        for a, b, c in segs:
            acc(S, a, b, agg, 'agent:' + c)
tot = {}
for k in sorted(agg):
    n, m, c = agg[k]
    print(f"{k:28} tokens {n:9d}  outside64k {m/n:6.2%}  of which in context {c/max(m,1):6.1%}")
    t = tot.setdefault(k.split(':')[0], [0, 0, 0]); t[0] += n; t[1] += m; t[2] += c
for k, (n, m, c) in tot.items():
    print(f"{'ALL '+k:28} tokens {n:9d}  outside64k {m/n:6.2%}  of which in context {c/max(m,1):6.1%}")
