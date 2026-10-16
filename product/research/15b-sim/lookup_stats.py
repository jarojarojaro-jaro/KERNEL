"""Per-position context-lookup statistics (HyperQwen-style suffix lookup).

For every output position p of every segment, with history = stream[:p] (window W tokens):
  m[p] = length of the longest suffix match (NMIN..NMAX tokens; 0 = none), ties -> most recent
  v[p] = how many continuation tokens the match supplies (<= KMAX), overlap with the suffix allowed
  r[p] = how many of those continuation tokens equal the real next tokens (capped at segment end)
The real tokens are the realized trajectory, so for exact-match verification (greedy, or
sample-and-match with one RNG draw per emitted token) this is an exact simulation, not an estimate.
"""
import json
import pickle
import sys

import numpy as np

import os
NMIN, NMAX, WINDOW, CAND = 4, 12, 131072, 64
KMAX = int(os.environ.get("KMAX", "15"))
P1 = np.uint64(0x9E3779B97F4A7C15)


def ngram_hash(s):
    s = s.astype(np.uint64)
    h = np.zeros(len(s), dtype=np.uint64)
    for j in range(NMIN):
        sh = np.zeros(len(s), dtype=np.uint64)
        sh[NMIN - 1:] = s[NMIN - 1 - j: len(s) - j]
        h = (h * P1) ^ (sh + np.uint64(j + 1))
    h[:NMIN - 1] = np.uint64(0)
    return h  # h[e] = hash of the n-gram ending at e


def stats_for_stream(S, segs):
    N = len(S)
    h = ngram_hash(S)
    order = np.lexsort((np.arange(N), h))
    Hs, Es = h[order], order.astype(np.int64)
    res = []
    for a, b, cls in segs:
        L = b - a
        m = np.zeros(L, np.int8)
        v = np.zeros(L, np.int8)
        r = np.zeros(L, np.int8)
        for i in range(L):
            p = a + i
            if p - 1 < NMIN - 1:
                continue
            key = h[p - 1]
            lo = np.searchsorted(Hs, key, 'left')
            hi = np.searchsorted(Hs, key, 'right')
            if hi == lo:
                continue
            blk = Es[lo:hi]
            # candidate ends e < p-1 and e >= p-1-WINDOW, most recent first
            j = np.searchsorted(blk, p - 1, 'left')
            k0 = np.searchsorted(blk, max(NMIN - 1, p - 1 - WINDOW), 'left')
            if j <= k0:
                continue
            cand = blk[max(k0, j - CAND):j][::-1]
            # vectorized backward match length up to NMAX
            offs = np.arange(NMAX)
            suf_idx = p - 1 - offs
            suf = np.where(suf_idx >= 0, S[np.maximum(suf_idx, 0)], -1)
            cidx = cand[:, None] - offs[None, :]
            cv = np.where(cidx >= 0, S[np.maximum(cidx, 0)], -2)
            eq = (cv == suf[None, :]) & (suf_idx[None, :] >= 0)
            ml = np.where(eq.all(1), NMAX, eq.argmin(1))
            best = int(ml.max())
            if best < NMIN:
                continue
            e = int(cand[int(np.argmax(ml))])  # first max = most recent
            vv = min(KMAX, p - 1 - e)
            prop = S[e + 1:e + 1 + vv]
            fut = S[p:min(b, p + vv)]
            n = min(len(prop), len(fut))
            neq = np.nonzero(prop[:n] != fut[:n])[0]
            rr = int(neq[0]) if len(neq) else n
            m[i], v[i], r[i] = best, vv, rr
        res.append((cls, m, v, r))
    return res


def main(which):
    out = []
    if which == 'agent':
        data = pickle.load(open('/tmp/specsim/agent_streams.pkl', 'rb'))
        for n, (name, S, segs) in enumerate(data):
            for cls, m, v, r in stats_for_stream(S, segs):
                out.append((name, cls, m, v, r))
            print(n, len(data), file=sys.stderr, flush=True)
    else:
        files = {
            'gen_p1': '/home/jaro/qwen-opt/mtp-train/data/gen_p1.jsonl',
            'gen_val': '/home/jaro/qwen-opt/mtp-train/pod-results/data/gen_val.jsonl',
            'gen_train': '/home/jaro/qwen-opt/mtp-train/pod-results/data/gen_train.jsonl',
        }
        for tag, f in files.items():
            for line in open(f):
                d = json.loads(line)
                cls = f"{tag}:{d.get('cls') or d.get('lang')}:{d.get('src') or d.get('cat')}"
                S = np.asarray(d['prompt_ids'] + d['resp_ids'], dtype=np.int32)
                a = len(d['prompt_ids'])
                for c, m, v, r in stats_for_stream(S, [(a, len(S), cls)]):
                    out.append((d['id'], c, m, v, r))
    pickle.dump(out, open(f'/tmp/specsim/lookup_{which}' + ('' if KMAX == 15 else str(KMAX)) + '.pkl', 'wb'))
    print('segments', len(out))


if __name__ == '__main__':
    main(sys.argv[1])
