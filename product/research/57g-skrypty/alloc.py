#!/usr/bin/env python3
"""R57g quantalloc: per-tensor type allocation for Qwen3.8-27B on the 24 GB XTX, fast-MMVQ types only.

Research only (user rule 2026-10-19: we do not change quants for speed). CPU only, no downloads.

Inputs (all local):
  ud-map.json            tensors of ~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf (udmap.py)
  map-UD-Q4_K_M.txt …    header-only tensor maps of Unsloth's sibling files (fetched 2026-10-21 by 16 MB byte range)
  klab trace now1/off    per-type MMVQ GB/s of the production verify step (report 47)

Sensitivity prior (no BF16 on disk -> no measured per-tensor KLD): the order in which Unsloth's own dynamic recipe
demotes a tensor when the file shrinks (XL -> Q4_K_M -> Q4_K_S -> IQ4_XS). Earlier demotion = less sensitive.
Ties: middle layers before edge layers. Protected: output head, token_embd, MTP block 64, attn_k/attn_v.

Output: alloc-<name>.txt (llama-quantize --tensor-type-file, one anchored regex per quantized tensor), alloc.json
(bytes/token, predicted step time and t/s).
"""
import json, re, sys, collections

BS = {'F32': (1, 4), 'F16': (1, 2), 'BF16': (1, 2), 'Q8_0': (32, 34), 'Q4_K': (256, 144), 'Q5_K': (256, 176),
      'Q6_K': (256, 210), 'Q3_K': (256, 110), 'IQ4_XS': (256, 136), 'IQ4_NL': (32, 18), 'IQ3_S': (256, 110),
      'IQ3_XXS': (256, 98), 'IQ2_XS': (256, 74), 'IQ2_XXS': (256, 66), 'IQ2_S': (256, 82), 'Q2_K': (256, 84)}
FAST = {'IQ4_XS', 'Q4_K', 'Q5_K', 'Q6_K', 'Q8_0'}
# klab profile traces/now1/off --by type (report 47, verify n5 + draft n1, 2026-10-21): effective GB/s per type
GBS = {'Q5_K': 776, 'IQ4_XS': 818, 'Q4_K': 738, 'Q6_K': 763, 'Q8_0': 489, 'IQ4_NL': 631, 'Q3_K': 747, 'IQ3_S': 436}
STEP_MS = 31.24            # klab trace now1/off client ms/step (MTP n=4 + lookup, 4.92 tok/step on that request mix)

xl = json.load(open('ud-map.json'))
T = {t['name']: t for t in xl}


def nbytes(name, ty):
    b = BS[ty]
    return T[name]['n'] // b[0] * b[1]


def streamed(name):        # read every decode step (token_embd is get_rows, blk.64 = MTP block read only by the draft)
    return not (name.startswith('token_embd') or name.startswith('blk.64.'))


def bpw(ty):
    return 8 * BS[ty][1] / BS[ty][0]


def sib(path):
    return {l.split()[0]: l.split()[1] for l in open(path)}


S = {q: sib(f'map-{q}.txt') for q in ('UD-Q4_K_M', 'UD-Q4_K_S', 'UD-IQ4_XS')}
PROTECT = re.compile(r'^(output\.weight|token_embd\.weight|blk\.64\.|blk\.\d+\.attn_[kv]\.weight)')
LAYERS = 64


def rank(name):
    """Lower = demote earlier (less sensitive per Unsloth's own recipe)."""
    ty = T[name]['type']
    r = 3
    for i, q in enumerate(('UD-Q4_K_M', 'UD-Q4_K_S', 'UD-IQ4_XS')):
        if bpw(S[q][name]) < bpw(ty):
            r = i
            break
    m = re.match(r'blk\.(\d+)\.', name)
    edge = min(int(m[1]), LAYERS - 1 - int(m[1])) if m else 0
    return (r, -edge, name)


DOWN = {'Q8_0': 'Q6_K', 'Q6_K': 'Q5_K'}


def build(target_gb, q5_to):
    """Greedy: walk tensors by rank, demote one fast step (Q5_K -> q5_to, Q6_K -> Q5_K, Q8_0 -> Q6_K) until the
    streamed bytes are target_gb below UD-Q4_K_XL. Non-fast UD types (IQ4_NL/Q3_K/IQ3_S) -> IQ4_XS first."""
    a = {n: t['type'] for n, t in T.items()}
    for n, ty in a.items():
        if ty in BS and ty not in FAST and len(T[n]['shape']) == 2 and ty not in ('F32', 'F16', 'BF16'):
            a[n] = 'IQ4_XS'
    base = sum(nbytes(n, T[n]['type']) for n in T if streamed(n))
    cur = lambda: sum(nbytes(n, a[n]) for n in T if streamed(n))
    cand = sorted((n for n in T if streamed(n) and not PROTECT.match(n) and a[n] in ('Q5_K', 'Q6_K', 'Q8_0')), key=rank)
    for n in cand:
        if base - cur() >= target_gb * 1e9:
            break
        a[n] = q5_to if a[n] == 'Q5_K' else DOWN[a[n]]
    return a


def predict(a):
    by = collections.Counter()
    for n in T:
        if streamed(n) and a[n] in GBS:
            by[a[n]] += nbytes(n, a[n])
    ud = collections.Counter()
    for n in T:
        if streamed(n) and T[n]['type'] in GBS:
            ud[T[n]['type']] += nbytes(n, T[n]['type'])
    d_ms = sum((by[t] - ud[t]) / 1e6 / GBS[t] for t in set(by) | set(ud))   # MB / (GB/s) = ms
    return d_ms, by


CANDS = {'qa1-iq4-1.0': (1.0, 'IQ4_XS'), 'qa2-q4k-1.0': (1.0, 'Q4_K'), 'qa3-iq4-1.5': (1.5, 'IQ4_XS')}
out = {}
base_file = sum(nbytes(n, T[n]['type']) for n in T)
base_st = sum(nbytes(n, T[n]['type']) for n in T if streamed(n))
for name, (tgt, to) in CANDS.items():
    a = build(tgt, to)
    f = sum(nbytes(n, a[n]) for n in T)
    st = sum(nbytes(n, a[n]) for n in T if streamed(n))
    d_ms, by = predict(a)
    ch = collections.Counter((re.sub(r'^blk\.\d+\.', '', n), T[n]['type'], a[n]) for n in T if a[n] != T[n]['type'])
    with open(f'alloc-{name}.txt', 'w') as fh:
        for n in sorted(T):
            if len(T[n]['shape']) == 2 and a[n] not in ('F32', 'F16', 'BF16'):
                fh.write('^' + re.escape(n) + '$=' + a[n].lower() + '\n')
    sp = STEP_MS / (STEP_MS + d_ms)
    out[name] = dict(target_gb=tgt, q5_to=to, file_gb=f / 1e9, d_file_gb=(f - base_file) / 1e9,
                     streamed_gb=st / 1e9, d_streamed_gb=(st - base_st) / 1e9, d_step_ms=d_ms,
                     speedup_step=sp, changes={f'{k[0]} {k[1]}->{k[2]}': v for k, v in ch.most_common()})
    print(f"{name}: file {f/1e9:.3f} GB ({(f-base_file)/1e9:+.3f}), streamed {st/1e9:.3f} ({(st-base_st)/1e9:+.3f}), "
          f"d_step {d_ms:+.3f} ms -> x{sp:.4f} (E0 79 -> {79*sp:.1f}, chat 100 -> {100*sp:.1f} t/s)")
    for k, v in ch.most_common(12):
        print(f"    {k[0]:22s} {k[1]:7s}->{k[2]:7s} x{v}")
# reference: Unsloth's own sibling at the same size (types incl. non-fast ones)
for q in ('UD-Q4_K_M', 'UD-Q4_K_S'):
    a = {n: S[q][n] for n in T}
    st = sum(nbytes(n, a[n]) for n in T if streamed(n))
    d_ms, _ = predict(a)
    sp = STEP_MS / (STEP_MS + d_ms)
    out[q] = dict(file_gb=sum(nbytes(n, a[n]) for n in T) / 1e9, streamed_gb=st / 1e9, d_streamed_gb=(st - base_st) / 1e9,
                  d_step_ms=d_ms, speedup_step=sp)
    print(f"{q}: streamed {st/1e9:.3f} ({(st-base_st)/1e9:+.3f}), d_step {d_ms:+.3f} ms -> x{sp:.4f}")
json.dump(out, open('alloc.json', 'w'), indent=1)
