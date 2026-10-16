"""Speculation policies replayed on the per-position lookup statistics.

Policies (verify width W = 1 + drafts):
  PLAIN      one token per forward
  LO-W       lookup only: if a match (m >= 4) supplies k tokens, verify 1+min(k, W-1); else plain step
  MTP4       our production: MTP chain of 4 drafts, W = 5
  HYB-W      MTP 4 drafts + lookup (HyperQwen LABD rules): head positions 0..3 from the lookup when m >= 6,
             tail positions 4..W-2 from the lookup when the head came from it; the long block is scheduled only
             after two consecutive saturated steps with a tail available (one step stale), held 3 more steps
  HYB-W-skip same, but the MTP chain is not run when the lookup covers the whole head (saves the draft cost)
  HYB-W-on   long block always scheduled when a tail is available (no copy-running test)
MTP correctness models:
  ind  each MTP draft at depth j correct with prob c (independent of copyability)
  cor  MTP draft at depth j correct if the lookup proposal is correct there, else with prob c
Cost model (RX 7900 XTX, ROCm, PM4, Qwen3.8-27B UD-Q4_K_XL, KV q4_0): see COST below.
"""
import math
import pickle
import sys
from collections import defaultdict

import numpy as np

# measured: server MTP n=4 step 27.74 ms (final-qwen); MTP 4-draft graph 3.62 ms (S2, IQ4_XS);
# plain tg128 43.2 t/s -> 23.15 ms; verify width deltas from k4/vcost_qwen-k4b.csv (llama-bench, d=2048)
VC = {2: 26.843, 3: 27.437, 4: 28.141, 5: 28.802, 6: 29.651, 7: 30.228, 8: 31.279, 9: 33.099, 10: 33.413,
      11: 33.880, 12: 34.026, 13: 34.398, 14: 34.672, 15: 35.079, 16: 35.892}
V5 = 27.74 - 3.62
DRAFT_MS = 3.62
SKIP_SAVE = 2.7  # [INFERENCE] the chain still needs a catch-up of the accepted rows later


def tiles(w):
    return math.ceil(6 * w / 16)


def V(w, att_ms_per_tile=0.0):
    base = 23.15 if w == 1 else V5 + (VC[w] - VC[5])
    return base + att_ms_per_tile * max(0, tiles(w) - tiles(5))


def solve_c(al, n=4):
    lo, hi = 0.0, 1.0
    for _ in range(60):
        c = (lo + hi) / 2
        if sum(c ** j for j in range(n + 1)) < al:
            lo = c
        else:
            hi = c
    return c


def mtp_run(rng, c, r_lu, depth, model):
    """Leading correct MTP drafts (<= depth)."""
    k = 0
    while k < depth:
        if model == 'cor' and r_lu > k:
            k += 1
            continue
        if rng.random() < c:
            k += 1
        else:
            break
    return k


def simulate(seg, policy, W, c, model, rng, att=0.0):
    m, v, r = seg
    L = len(m)
    i = 0
    steps = 0
    ms = 0.0
    prev_want = [False, False]
    sticky = 0
    long_next = False
    tail_tokens = 0
    while i < L:
        mi, vi, ri = int(m[i]), int(v[i]), int(r[i])
        if policy == 'PLAIN':
            acc, w, cost = 0, 1, V(1, att)
        elif policy == 'LO':
            if mi >= 4 and vi > 0:
                k = min(vi, W - 1)
                acc = min(ri, k)
                w = 1 + k
            else:
                acc, w = 0, 1
            cost = V(w, att)
        elif policy == 'MTP4':
            acc = mtp_run(rng, c, ri if mi >= 4 else 0, 4, model)
            w, cost = 5, V(5, att) + DRAFT_MS
        else:  # HYB variants
            take_head = mi >= 6 and vi > 0
            lu_ok = ri if mi >= 4 else 0
            if take_head:
                h = min(ri, vi, 4)
                if h == min(vi, 4) and vi < 4:  # lookup ran out inside the head: MTP continues
                    h += mtp_run(rng, c, 0, 4 - vi, 'ind')
            else:
                h = mtp_run(rng, c, lu_ok, 4, model)
            has_tail = take_head and mi >= 6 and vi > 4
            use_long = has_tail if policy == 'HYB-on' else long_next
            if use_long and W > 5:
                w = W
                acc = h
                if h == 4 and take_head:
                    acc = min(ri, vi, W - 1)
                    acc = max(acc, 4)
                    tail_tokens += acc - 4
            else:
                w, acc = 5, h
            skip = policy == 'HYB-skip' and take_head and vi >= 4
            cost = V(w, att) + (DRAFT_MS - SKIP_SAVE if skip else DRAFT_MS)
            emitted = acc + 1
            want = has_tail and emitted >= 5
            if want and prev_want[-1]:
                long_next, sticky = True, 3
            elif sticky > 0:
                long_next, sticky = True, sticky - 1
            else:
                long_next = False
            prev_want = [prev_want[-1], want]
        acc = min(acc, L - i - 1)
        i += acc + 1
        steps += 1
        ms += cost
    return steps, ms, tail_tokens


def class_al(cls):
    """Measured MTP n=4 tok/step for the matching spec_sweep class; agent outputs are an assumption."""
    if not cls.startswith('gen_'):
        return 3.2  # agent outputs: between en-code 3.05 and pl-kod 3.47 [ASSUMPTION]
    _, lang, src = cls.split(':')
    if src == 'spec_sweep':  # gen_val holds 2 pl (proza/tech), 2 en (chat/tech), 2 code prompts per lang tag
        return {'pl': (2.77 + 3.29) / 2, 'en': (2.43 + 3.00) / 2, 'code': (3.47 + 3.05) / 2}[lang]
    if lang == 'code' or src in ('code', 'selfoss'):
        return 3.47 if lang == 'pl' else 3.05
    if src == 'tech':
        return 3.29 if lang == 'pl' else 3.00
    return 2.77 if lang == 'pl' else 2.43


def group(cls):
    if cls.startswith('gen_'):
        t, lang, src = cls.split(':')
        if src == 'spec_sweep':
            return f'spec_sweep-{lang}'
        if t == 'gen_p1':
            return f'p1-{lang}-{src}'
        return f'{lang}-{src}'
    return 'agent-' + cls


def main():
    segs = []
    for f in sys.argv[1:]:
        segs += pickle.load(open(f, 'rb'))
    groups = defaultdict(list)
    for name, cls, m, v, r in segs:
        if len(m) < 2:
            continue
        groups[group(cls)].append((cls, (m, v, r)))
    rows = []
    for g, items in sorted(groups.items()):
        ntok = sum(len(s[0]) for _, s in items)
        allm = np.concatenate([s[0] for _, s in items]).astype(int)
        allr = np.concatenate([s[2] for _, s in items]).astype(int)
        cop1 = float(((allm >= 4) & (allr >= 1)).mean())
        cop8 = float(((allm >= 6) & (allr >= 8)).mean())
        al = class_al(items[0][0])
        c = solve_c(al)
        res = {'group': g, 'segs': len(items), 'tokens': ntok, 'copy1': cop1, 'copy8': cop8, 'AL_mtp_meas': al, 'c': c}
        for att in (0.0, 3.5):
            for pol, W in (('PLAIN', 1), ('LO', 8), ('LO', 16), ('MTP4', 5), ('HYB', 8), ('HYB', 16), ('HYB-skip', 16),
                           ('HYB-on', 16)):
                for model in (('ind', 'cor') if pol not in ('PLAIN', 'LO') else ('ind',)):
                    st = ms = tt = 0
                    seeds = 3 if pol not in ('PLAIN', 'LO') else 1
                    for sd in range(seeds):
                        rng = np.random.default_rng(1000 + sd)
                        for cls, s in items:
                            a, b, t3 = simulate(s, pol if pol != 'HYB' else 'HYB', W, c, model, rng, att)
                            st += a
                            ms += b
                            tt += t3
                    key = f'{pol}-W{W}/{model}/att{att}'
                    res[key] = (ntok * seeds / st, ntok * seeds / ms * 1000, tt / seeds / ntok)
        rows.append(res)
    pickle.dump(rows, open('/tmp/specsim/policy_rows_' + sys.argv[1].split('/')[-1], 'wb'))
    for res in rows:
        print(f"\n## {res['group']}  segs={res['segs']} tokens={res['tokens']} copy1={res['copy1']:.3f} "
              f"copy8={res['copy8']:.3f} AL_mtp={res['AL_mtp_meas']} c={res['c']:.3f}")
        for k, (tps_step, tps, tail) in res.items() if False else []:
            pass
        for k in [k for k in res if '/' in k]:
            a, b, t3 = res[k]
            print(f'  {k:28s} tok/step {a:5.2f}  t/s {b:6.1f}  tail-share {t3:.3f}')


if __name__ == '__main__':
    main()
