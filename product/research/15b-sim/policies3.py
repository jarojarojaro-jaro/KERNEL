"""Upper bound for long drafter-free copy chains (0x7067 / llama.cpp ngram-mod style, up to 64 tokens a round).
EXT-W16 entry (calibrated MTP model as policies2), then lookup-only chain blocks of Wc-1 tokens (Wc = 16/32/64)
until the first rejection. Verify cost beyond 16 columns is NOT measured on our stack: V(32), V(64) are scenarios.
Short context only (no attention adder)."""
import os
import pickle
import sys

import numpy as np

sys.path.insert(0, '/tmp/specsim')
import policies  # noqa: E402
from policies import DRAFT_MS, class_al, group, solve_c  # noqa: E402
from policies2 import CalMTP  # noqa: E402

SCEN = {'opt': {32: 40.0, 64: 50.0}, 'pes': {32: 48.0, 64: 65.0}}


def Vx(w, scen):
    if w <= 16:
        return policies.V(w)
    return SCEN[scen][32] if w <= 32 else SCEN[scen][64]


def replay(Wc, scen, m, v, r, mtp, W=16):
    L = len(m)
    i = steps = 0
    ms = 0.0
    prev_want = False
    sticky = 0
    long_next = False
    chain = False
    while i < L:
        mi, vi, ri = int(m[i]), int(v[i]), int(r[i])
        lu = min(ri, 15) if mi >= 4 else 0
        if Wc == 0:  # baseline MTP4
            acc, cost = mtp.run(i, lu), Vx(5, scen) + DRAFT_MS
        elif chain and mi >= 6 and vi >= 1:
            k = min(vi, Wc - 1)
            acc, cost = min(ri, k), Vx(1 + k, scen)
            chain = acc == k and vi >= Wc - 1
        else:
            chain = False
            h = mtp.run(i, lu)
            has_tail = h == 4 and mi >= 6 and ri >= 4 and vi > 4
            w, acc = 5, h
            if long_next:
                w = W
                if has_tail:
                    acc = max(4, min(ri, vi, W - 1))
            cost = Vx(w, scen) + DRAFT_MS
            want = has_tail and acc + 1 >= 5
            if want and prev_want:
                long_next, sticky = True, 3
            elif sticky > 0:
                long_next, sticky = True, sticky - 1
            else:
                long_next = False
            prev_want = want
            if w == W and acc == W - 1:
                chain = True
        acc = min(acc, L - i - 1)
        i += acc + 1
        steps += 1
        ms += cost
    return steps, ms


def main(path):
    segs = pickle.load(open(path, 'rb'))
    groups = {}
    for name, cls, m, v, r in segs:
        if len(m) >= 2:
            groups.setdefault(group(cls), []).append((cls, m, v, r))
    tot = {}
    for scen in ('opt', 'pes'):
        print(f'\n-- scenario {scen}: V(32)={SCEN[scen][32]} V(64)={SCEN[scen][64]} ms --')
        for g, items in sorted(groups.items()):
            ntok = sum(len(x[1]) for x in items)
            c = solve_c(class_al(items[0][0]))
            base = None
            cells = []
            for Wc in (0, 16, 32, 64):
                st = ms = 0
                rng = np.random.default_rng(11)
                for cls, m, v, r in items:
                    a, b = replay(Wc, scen, m, v, r, CalMTP(c, rng))
                    st += a
                    ms += b
                tps = ntok / ms * 1000
                base = base or tps
                tot.setdefault((scen, Wc), [0, 0.0])
                tot[(scen, Wc)][0] += ntok
                tot[(scen, Wc)][1] += ms
                cells.append(f"{'MTP4' if Wc == 0 else 'EXT16+CH' + str(Wc)} {ntok/st:.2f}/{tps:.1f} ({tps/base-1:+.1%})")
            print(f'{g:22s} {ntok:8d}  ' + '  '.join(cells))
        b = tot[(scen, 0)]
        print('ALL (token-weighted)', '  '.join(f'Wc={Wc}: {t[0]/t[1]*1000:.1f} ({(t[0]/t[1])/(b[0]/b[1])-1:+.1%})'
                                               for (s, Wc), t in tot.items() if s == scen))


if __name__ == '__main__':
    main(sys.argv[1])
