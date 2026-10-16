"""Second-round policies, with the MTP/lookup correlation calibrated on real MTP chains (mtp_join.py):
  P(MTP draft at depth k ok | lookup ok to depth k, MTP ok before) = Q[k] = 0.968, 0.969, 0.974, 0.984
  otherwise MTP ok with prob c (class calibration as in policies.py)
Policies:
  MTP4        production (W=5)
  HYB-W       HyperQwen LABD rules (lookup overrides the head when m>=6; tail when the head is the lookup's)
  EXT-W       MTP keeps the head; the lookup only appends a tail (positions 4..W-2) when the 4 MTP drafts equal the
              lookup's first 4 tokens; long block scheduled after 2 saturated steps, held 3 (as LABD)
  EXT-W+CH    EXT plus drafter-free chains: after a step that accepted a whole long block, the next step proposes
              W-1 lookup tokens without running MTP, until the first rejection (HyperQwen CHAIN / Strata lookup window)
Also replays EXT/CH with the REAL MTP chains of gen_p1 (no model).
"""
import pickle
import sys

import numpy as np

sys.path.insert(0, '/tmp/specsim')
from policies import DRAFT_MS, V, class_al, group, solve_c  # noqa: E402

Q = (0.968, 0.969, 0.974, 0.984)


class CalMTP:
    def __init__(self, c, rng):
        self.c, self.rng = c, rng

    def run(self, i, r_lu, depth=4):
        k = 0
        while k < depth:
            p = Q[k] if r_lu > k else self.c
            if self.rng.random() < p:
                k += 1
            else:
                break
        return k


class RealMTP:
    def __init__(self, ok):
        self.ok = ok

    def run(self, i, r_lu, depth=4):
        k = 0
        while k < depth and self.ok[i, k]:
            k += 1
        return k


def replay(policy, W, m, v, r, mtp, att=0.0):
    L = len(m)
    i = steps = 0
    ms = 0.0
    prev_want = False
    sticky = 0
    long_next = False
    chain = False
    while i < L:
        mi, vi, ri = int(m[i]), int(v[i]), int(r[i])
        lu = ri if mi >= 4 else 0
        if policy == 'MTP4':
            acc, cost = mtp.run(i, lu), V(5, att) + DRAFT_MS
        elif chain and mi >= 6 and vi >= 1:
            k = min(vi, W - 1)
            acc, cost = min(ri, k), V(1 + k, att)
            chain = acc == k and k == W - 1
        else:
            chain = False
            if policy == 'HYB':
                take = mi >= 6 and vi > 0
                h = min(ri, vi, 4) if take else mtp.run(i, lu)
                if take and vi < 4 and h == vi:
                    h += mtp.run(i, 0, 4 - vi)
                agree4 = take and h == 4
            else:  # EXT / EXT+CH: MTP head untouched
                h = mtp.run(i, lu)
                agree4 = h == 4 and mi >= 4 and ri >= 4  # MTP drafts == lookup tokens on the head
            has_tail = agree4 and mi >= 6 and vi > 4
            w, acc = 5, h
            if long_next and W > 5:
                w = W
                if has_tail:
                    acc = max(4, min(ri, vi, W - 1))
            cost = V(w, att) + DRAFT_MS
            want = has_tail and acc + 1 >= 5
            if want and prev_want:
                long_next, sticky = True, 3
            elif sticky > 0:
                long_next, sticky = True, sticky - 1
            else:
                long_next = False
            prev_want = want
            if policy == 'EXT+CH' and w == W and acc == W - 1:
                chain = True
        acc = min(acc, L - i - 1)
        i += acc + 1
        steps += 1
        ms += cost
    return steps, ms


POLS = (('MTP4', 5), ('HYB', 16), ('EXT', 8), ('EXT', 16), ('EXT+CH', 8), ('EXT+CH', 16))


def run_lookup_file(path, seeds=int(__import__("os").environ.get("SEEDS", "3"))):
    segs = pickle.load(open(path, 'rb'))
    groups = {}
    for name, cls, m, v, r in segs:
        if len(m) >= 2:
            groups.setdefault(group(cls), []).append((cls, m, v, r))
    for att in (0.0, 3.5):
        print(f'\n-- calibrated MTP model, att={att} ms/tile: tok/step / t/s (gain vs MTP4) --')
        for g, items in sorted(groups.items()):
            ntok = sum(len(x[1]) for x in items)
            c = solve_c(class_al(items[0][0]))
            base = None
            cells = []
            for pol, W in POLS:
                st = ms = 0
                for sd in range(seeds):
                    rng = np.random.default_rng(7 + sd)
                    for cls, m, v, r in items:
                        a, b = replay(pol, W, m, v, r, CalMTP(c, rng), att)
                        st += a
                        ms += b
                tps = ntok * seeds / ms * 1000
                base = base or tps
                cells.append(f'{pol}-W{W} {ntok*seeds/st:.2f}/{tps:.1f} ({tps/base-1:+.1%})')
            print(f'{g:22s} {ntok:8d}  ' + '  '.join(cells))


def run_real_p1():
    from mtp_join import per_seq
    seqs = list(per_seq())
    by = {}
    for s in seqs:
        by.setdefault(s[1].split(':', 1)[1], []).append(s)
    by['ALL'] = seqs
    for att in (0.0, 3.5):
        print(f'\n-- REAL MTP chains (gen_p1), att={att}: tok/step / t/s (gain vs MTP4) --')
        for cls, ss in sorted(by.items()):
            ntok = sum(len(s[2]) for s in ss)
            base = None
            cells = []
            for pol, W in POLS:
                st = ms = 0
                for _, _, m, v, r, ok in ss:
                    a, b = replay(pol, W, m, v, r, RealMTP(ok), att)
                    st += a
                    ms += b
                tps = ntok / ms * 1000
                base = base or tps
                cells.append(f'{pol}-W{W} {ntok/st:.2f}/{tps:.1f} ({tps/base-1:+.1%})')
            print(f'{cls:14s} {ntok:6d}  ' + '  '.join(cells))


if __name__ == '__main__':
    if sys.argv[1] == 'real':
        run_real_p1()
    else:
        run_lookup_file(sys.argv[1])
