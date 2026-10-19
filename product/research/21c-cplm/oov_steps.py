"""Upper bound: tok/step of MTP n=4 with full-vocab draft vs 64k draft vocab vs 64k + context tokens.
Chain profile CUM (measured, 15b-sim/results.txt:1) is used as the full-vocab chain; a draft whose target token
is outside the draft vocab is necessarily wrong, so the chain is truncated there. Upper bound because MTP
accuracy on rare tokens is below average."""
import json, pickle, sys
import numpy as np
CUM = np.array([0.779, 0.565, 0.404, 0.293])
V = np.loadtxt('/home/jaro/models/draft/draft_vocab_qwen38.txt', dtype=np.int64)[:65536]
inv = np.zeros(300000, bool); inv[V] = True
rng = np.random.default_rng(7)
def run(S, a, b, agg, cls):
    seen = np.zeros(300000, bool); seen[S[:a]] = True
    out = S[a:b]; L = len(out)
    ok64 = inv[out].copy()
    okctx = ok64.copy()
    for i, t in enumerate(out):
        if seen[t]: okctx[i] = True
        seen[t] = True
    u = rng.random(L)
    res = []
    for ok in (np.ones(L, bool), okctx, ok64):
        p = st = 0
        while p < L:
            k = int((u[p] < CUM).sum())
            # drafts predict out[p+1 .. p+k]; out[p] is the verified token of this step
            j = 0
            while j < k and p + 1 + j < L and ok[p + 1 + j]:
                j += 1
            p += 1 + j; st += 1
        res.append(st)
    g = agg.setdefault(cls, np.zeros(4)); g += [L] + res
agg = {}
for line in open('/home/jaro/qwen-opt/mtp-train/data/gen_p1.jsonl'):
    d = json.loads(line)
    S = np.asarray(d['prompt_ids'] + d['resp_ids'], dtype=np.int64)
    run(S, len(d['prompt_ids']), len(S), agg, 'chat:' + str(d.get('lang')))
data = pickle.load(open('/tmp/specsim/agent_streams.pkl', 'rb'))
for j in np.random.default_rng(1).permutation(len(data))[:60]:
    _, S, segs = data[j]; S = S.astype(np.int64)
    for a, b, c in segs:
        run(S, a, b, agg, 'agent:' + c)
print(f"{'class':24} tok/step full | 64k+ctx | 64k   (64k+ctx vs 64k)")
for k in sorted(agg):
    L, f, c, s = agg[k]
    print(f"{k:24} {L/f:5.3f} | {L/c:5.3f} | {L/s:5.3f}   {s/c-1:+.2%}")
