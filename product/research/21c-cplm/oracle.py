import bisect
"""Upper bound for a learned copy pointer (CPLM-style) over our n-gram lookup tail.

Per output position p (history = stream[:p]):
  BASE : server policy (longest suffix 4..12, <=64 most recent candidates, tie -> most recent)
  ORA4 : oracle best continuation among the same 64 candidates (perfect re-ranking pointer)
  ORA2 : oracle best continuation among <=64 most recent 2-gram matches (pointer may fire earlier)
  ORA1 : oracle best continuation among <=64 most recent 1-gram matches (current token)
r = number of proposed continuation tokens (<=15) equal to the real next tokens.
Step model (common random numbers for all policies): MTP n=4 accepts k drafts with the measured
cumulative profile 0.779/0.565/0.404/0.293; if the copy proposal has r >= 4, the step advances
1 + max(k, r) (MTP covers d1..d4 on copies, P=0.968 measured), else 1 + k.
Only aggregate statistics are printed.
"""
import json
import pickle
import sys
from collections import defaultdict

import numpy as np

NMAX, CAND, KMAX = 12, 64, 15
CUM = np.array([0.779, 0.565, 0.404, 0.293])


def build_index(S, n):
    idx = defaultdict(list)
    for e in range(n - 1, len(S)):
        idx[tuple(S[e - n + 1:e + 1])].append(e)
    return idx


def eval_cands(S, p, b, cands):
    """return (ml, r) arrays for candidate ends (most recent first)."""
    out = []
    for e in cands:
        ml = 0
        while ml < NMAX and e - ml >= 0 and S[e - ml] == S[p - 1 - ml]:
            ml += 1
        vv = min(KMAX, p - 1 - e)
        r = 0
        while r < vv and p + r < b and S[e + 1 + r] == S[p + r]:
            r += 1
        out.append((ml, r))
    return out


def recent(idx, key, p, k=CAND):
    lst = idx.get(key)
    if not lst:
        return []
    j = bisect.bisect_left(lst, p - 1)  # ends < p-1
    return lst[max(0, j - k):j][::-1]

def agree(ev):
    """candidate whose continuation starts with the 4 (correct) MTP drafts: longest suffix, then most recent."""
    ok = [(m, r) for m, r in ev if r >= 4]
    if not ok:
        return 0
    best = max(m for m, _ in ok)
    return next(r for m, r in ok if m == best)



def stream_rs(S, segs):
    S = [int(x) for x in S]
    i1, i2, i4 = build_index(S, 1), build_index(S, 2), build_index(S, 4)
    res = []
    for a, b, cls in segs:
        L = b - a
        R = np.zeros((6, L), np.int8)
        M = np.zeros(L, np.int8)  # best backward suffix match of the BASE lookup
        for i in range(L):
            p = a + i
            if p < 2:
                continue
            c1 = recent(i1, tuple(S[p - 1:p]), p)
            c2 = recent(i2, tuple(S[p - 2:p]), p) if p >= 2 else []
            c4 = recent(i4, tuple(S[p - 4:p]), p) if p >= 4 else []
            if c4:
                ev = eval_cands(S, p, b, c4)
                best = max(m for m, _ in ev)
                if best >= 4:
                    R[0, i] = next(r for m, r in ev if m == best)
                    R[1, i] = max(r for _, r in ev)
                    R[4, i] = agree(ev)
                    M[i] = best
            if c2:
                ev2 = eval_cands(S, p, b, c2)
                R[2, i] = max(r for _, r in ev2)
                R[5, i] = agree(ev2)
            if c1:
                R[3, i] = max(r for _, r in eval_cands(S, p, b, c1))
        res.append((cls, R, M))
    return res


T5, TW16 = 28.74, 6.40  # ms: MTP4 W5 step on chat (16b:19), V16 - V5 at 2k (16b:20)


POLS = ['BASE', 'ORA4', 'ORA2', 'ORA1', 'AGR4', 'AGR2', 'ORA1-HYB']
ROW = [0, 1, 2, 3, 4, 5, 3]
MMIN = 6  # server trigger: match >= 6 and all 4 MTP drafts equal lookup tokens (16b:32)


def steps(R, M, rng_u):
    """walk one segment; returns tokens, steps[], ms[].
    BASE      : server tail - fires when M >= 6 and MTP chain fully right (k == 4) and lookup agrees (r >= 4).
    ORA4/2/1  : same EXT mechanism (needs k == 4), oracle picks best candidate among 4-/2-/1-gram matches.
    AGR4/2    : realizable, training-free: among 4-/2-gram candidates keep those whose first 4 continuation
                tokens equal the 4 MTP drafts (= truth when k == 4), then longest suffix, then most recent.
    ORA1-HYB  : oracle pointer may also replace a failing MTP chain (fires whenever r >= 4 and r > k).
    Wide (W16) cost is paid only when the tail is used (BASE trigger ~ tail accepted, 16b:96,112)."""
    L = R.shape[1]
    st_out, ms_out = [], []
    for pol in range(len(POLS)):
        row = R[ROW[pol]]
        p = st = 0
        ms = 0.0
        while p < L:
            k = int((rng_u[p] < CUM).sum())
            r = int(row[p])
            if pol == 0:
                use = M[p] >= MMIN and k == 4 and r > 4
            elif POLS[pol] != 'ORA1-HYB':
                use = k == 4 and r > 4
            else:
                use = r >= 4 and r > k
            p += 1 + (r if use else k)
            st += 1
            ms += T5 + (TW16 if use and r > 4 else 0.0)
        st_out.append(st)
        ms_out.append(ms)
    return L, st_out, ms_out


def main():
    NP = len(POLS)
    agg = defaultdict(lambda: np.zeros(1 + 2 * NP))
    rng = np.random.default_rng(1)
    srcs = []
    if 'agent' in sys.argv[1:]:
        data = pickle.load(open('/tmp/specsim/agent_streams.pkl', 'rb'))
        lim = int(sys.argv[2]) if len(sys.argv) > 2 else len(data)
        sel = rng.permutation(len(data))[:lim]
        srcs += [(data[j][1], data[j][2], 'agent:') for j in sel]
    if 'chat' in sys.argv[1:]:
        for line in open('/home/jaro/qwen-opt/mtp-train/data/gen_p1.jsonl'):
            d = json.loads(line)
            S = np.asarray(d['prompt_ids'] + d['resp_ids'], dtype=np.int32)
            srcs.append((S, [(len(d['prompt_ids']), len(S), f"{d.get('lang')}:{d.get('src') or d.get('cat')}")], 'chat:'))
    for n, (S, segs, pre) in enumerate(srcs):
        for cls, R, M in stream_rs(S, segs):
            u = rng.random(R.shape[1])
            L, st, ms = steps(R, M, u)
            agg[pre + cls] += np.array([L] + st + ms)
        if n % 50 == 0:
            print(n, len(srcs), file=sys.stderr, flush=True)
    def row(name, v):
        tok = v[0] / v[1:1 + NP]
        tps = 1000 * v[0] / v[1 + NP:]
        print(f"{name:26} {int(v[0]):9d} " + ' '.join(f"{x:5.2f}" for x in tok) + ' | ' +
              ' '.join(f"{x:6.1f}" for x in tps) + ' | ' +
              ' '.join(f"{tps[j] / tps[0] - 1:+.1%}" for j in range(1, NP)))

    print(f"{'class':26} {'tokens':>9} tok/step {' '.join(POLS)} | t/s (model) same | t/s vs BASE {' '.join(POLS[1:])}")
    tot = defaultdict(lambda: np.zeros(1 + 2 * NP))
    for k in sorted(agg):
        row(k, agg[k])
        tot[k.split(':')[0]] += agg[k]
    for k, v in tot.items():
        row('ALL ' + k, v)


if __name__ == '__main__':
    main()
