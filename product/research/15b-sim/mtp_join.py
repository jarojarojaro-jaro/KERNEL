"""Join real MTP draft chains (mtp-train ext_p1/chain.bin: production greedy 4-draft chain for every response
position of gen_p1, 57 Qwen3.8-27B answers at T=1) with the context-lookup statistics on the same positions.

1. Conditional MTP accuracy given lookup correctness (how much of the copy signal MTP already captures).
2. Exact replay of MTP4 / HYB policies with the REAL drafts (no Bernoulli model).
"""
import json
import pickle
import sys

import numpy as np

sys.path.insert(0, '/tmp/specsim')
from policies import DRAFT_MS, SKIP_SAVE, V  # noqa: E402

ROWS = [json.loads(l) for l in open('/home/jaro/qwen-opt/mtp-train/data/gen_p1.jsonl')]
CH = np.fromfile('/home/jaro/qwen-opt/mtp-train/data/ext_p1/chain.bin', dtype=np.int32).reshape(-1, 4)
LK = {d[0]: d for d in pickle.load(open('/tmp/specsim/lookup_chat.pkl', 'rb')) if d[1].startswith('gen_p1')}
assert sum(len(r['resp_ids']) for r in ROWS) == len(CH)


def per_seq():
    off = 0
    for r in ROWS:
        resp = np.asarray(r['resp_ids'], np.int64)
        n = len(resp)
        ch = CH[off:off + n]
        off += n
        _, cls, m, v, rr = LK[r['id']]
        # mtp_ok[i, k]: chain row i (drafted with history up to resp[i-1]) has draft k == resp[i+k]
        ok = np.zeros((n, 4), bool)
        for k in range(4):
            idx = np.arange(0, n - k)
            ok[idx, k] = ch[idx, k] == resp[idx + k]
        yield r, cls, m.astype(int), v.astype(int), rr.astype(int), ok


def mtp_run(ok_row, depth=4):
    k = 0
    while k < depth and ok_row[k]:
        k += 1
    return k


def replay(policy, W, m, v, r, ok, att=0.0):
    L = len(m)
    i = steps = 0
    ms = 0.0
    prev_want = False
    sticky = 0
    long_next = False
    while i < L:
        mi, vi, ri = m[i], v[i], r[i]
        if policy == 'MTP4':
            acc, cost = mtp_run(ok[i]), V(5, att) + DRAFT_MS
        else:
            take_head = mi >= 6 and vi > 0
            if take_head:
                h = min(ri, vi, 4)
                if vi < 4 and h == vi:
                    h += mtp_run(ok[i, vi:], 4 - vi)  # approximation: MTP chain continues past the lookup
            else:
                h = mtp_run(ok[i])
            has_tail = take_head and vi > 4
            use_long = has_tail if policy == 'HYB-on' else long_next
            w, acc = 5, h
            if use_long and W > 5:
                w = W
                if h == 4 and take_head:
                    acc = max(4, min(ri, vi, W - 1))
            skip = policy == 'HYB-skip' and take_head and vi >= 4
            cost = V(w, att) + (DRAFT_MS - SKIP_SAVE if skip else DRAFT_MS)
            want = has_tail and acc + 1 >= 5
            if want and prev_want:
                long_next, sticky = True, 3
            elif sticky > 0:
                long_next, sticky = True, sticky - 1
            else:
                long_next = False
            prev_want = want
        acc = min(acc, L - i - 1)
        i += acc + 1
        steps += 1
        ms += cost
    return steps, ms


def main():
    seqs = list(per_seq())
    # 1. conditional accuracy at depth 1 (draft k=0 for position i)
    allm = np.concatenate([s[2] for s in seqs])
    allr = np.concatenate([s[4] for s in seqs])
    allok = np.concatenate([s[5] for s in seqs])
    lu1 = (allm >= 4) & (allr >= 1)
    lu_any = allm >= 4
    print('positions', len(allm), 'cum@1..4 (MTP realized):',
          ' '.join(f'{np.mean(np.cumprod(allok, 1)[:, k]):.3f}' for k in range(4)))
    print(f'lookup proposes (m>=4): {lu_any.mean():.3f}; lookup correct at d1: {lu1.mean():.3f}')
    print(f'P(MTP d1 ok | lookup d1 ok) = {allok[lu1, 0].mean():.3f}  (n={lu1.sum()})')
    print(f'P(MTP d1 ok | lookup proposes, wrong) = {allok[lu_any & ~lu1, 0].mean():.3f}  (n={(lu_any & ~lu1).sum()})')
    print(f'P(MTP d1 ok | no lookup) = {allok[~lu_any, 0].mean():.3f}  (n={(~lu_any).sum()})')
    for k in range(1, 4):
        sel = (allm >= 4) & (allr >= k + 1)
        print(f'P(MTP d{k+1} chain ok | lookup ok to d{k+1}) = {np.cumprod(allok, 1)[sel, k].mean():.3f} (n={sel.sum()}); '
              f'unconditional {np.cumprod(allok, 1)[:, k].mean():.3f}')
    sel6 = (allm >= 6) & (allr >= 8)
    print(f'long copy runs (m>=6, r>=8): {sel6.mean():.3f}; MTP full 4-chain ok there: {np.cumprod(allok,1)[sel6,3].mean():.3f}')
    # 2. replay per class
    by = {}
    for s in seqs:
        by.setdefault(s[1], []).append(s)
    by['ALL'] = seqs
    for att in (0.0, 3.5):
        print(f'\n-- exact replay with real MTP drafts, att={att} ms/tile (tok/step, t/s) --')
        for cls, ss in sorted(by.items()):
            ntok = sum(len(s[2]) for s in ss)
            out = []
            for pol, W in (('MTP4', 5), ('HYB', 8), ('HYB', 16), ('HYB-skip', 16), ('HYB-on', 16)):
                st = ms = 0
                for s in ss:
                    a, b = replay(pol, W, s[2], s[3], s[4], s[5], att)
                    st += a
                    ms += b
                out.append(f'{pol}-W{W} {ntok/st:.2f}/{ntok/ms*1000:.1f}')
            print(f'{cls:22s} n={ntok:6d}  ' + '  '.join(out))


if __name__ == '__main__':
    main()
