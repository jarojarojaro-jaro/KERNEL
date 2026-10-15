#!/usr/bin/env python3
"""Offline bitwise-equivalence check of two compiled gated_delta_net kernels (see gdnemu.py).

  gdncmp.py BASE.s BASE_FN FAST.s FAST_FN [--lag] [--l2] [--numeric]

Runs one wave of several launches (token counts, pending rows, state gather, CTA/wave positions) through both kernels
with symbolic float inputs and requires every written output word to be the same IEEE expression DAG. --numeric also
evaluates the DAGs on random inputs against a float64 reference of the recurrence (validates the emulator itself).
"""
import sys, random, struct, math, argparse
from collections import Counter
import gdnemu as E

S_V = 128

def init_fastdiv(d):
    L = 0
    while L < 32 and (1 << L) < d:
        L += 1
    mp = ((1 << 32) * ((1 << L) - d) // d + 1) & E.M32
    return (mp, L, d)

class Launch:
    def __init__(self, n_tokens, H=4, neqk1=2, n_seqs=1, lag=False, n_pend=0, K=1, gather=False, wg=(1, 0, 0),
                 tid_y=0, num_warps=4, seq_rows=3):
        self.__dict__.update(locals()); del self.__dict__['self']

def build(L):
    mem = E.Mem()
    S = S_V
    H, T, NS = L.H, L.n_tokens, L.n_seqs
    bases = iter(((i + 1) << 36) + 0xfff00000 for i in range(32))
    bufs = {}
    def fb(name, n, kind='f', init=None):
        bufs[name] = mem.add(E.Buf(name, next(bases), n, kind, init))
        return bufs[name]
    q = fb('q', S * L.neqk1 * T * NS); k = fb('k', S * L.neqk1 * T * NS)
    v = fb('v', S * H * T * NS); g = fb('g', H * T * NS); beta = fb('beta', H * T * NS)
    if L.gather:
        rows = L.seq_rows
        cs = fb('cache', rows * S * S * H)
        sidx = fb('state_idx', NS, 'i', {i: (2 - i) % rows for i in range(NS)})
    else:
        cs = fb('s0', S * S * H * NS)
        sidx = None
    dst = fb('dst', S * H * T * NS)
    st = fb('state', S * S * H * NS)
    R = H * (2 * S + 2)
    if L.lag:
        prs = 2 * L.K * R
        pend = fb('pend', prs * 2)
        info = fb('info', 4 * NS, 'i', {j * NS + s_: x for s_ in range(NS)
                                         for j, x in enumerate((0, 1, L.n_pend, 0 | (1 << 1)))})
    ka = {}
    def p32(o, x): ka[o // 4] = x & E.M32
    def p64(o, x): p32(o, x); p32(o + 4, x >> 32)
    p64(0, q.base); p64(8, k.base); p64(16, v.base); p64(24, g.base); p64(32, beta.base); p64(40, cs.base)
    p64(48, sidx.base if sidx else 0); p64(56, S * S * H if L.gather else 0)
    p64(64, dst.base); p64(72, st.base); p64(80, H); p64(88, T); p64(96, NS)
    p64(104, S); p64(112, S * L.neqk1); p64(120, S * L.neqk1 * T)
    p64(128, S); p64(136, S * H); p64(144, S * H * T)
    p64(152, 1); p64(160, H); p64(168, H * T)
    m1 = init_fastdiv(L.neqk1); m3 = init_fastdiv(1)
    for i in range(3): p32(176 + 4 * i, m1[i]); p32(188 + 4 * i, m3[i])
    ka[200 // 4] = E.G.mk(('arg', 'scale')); ka[204 // 4] = E.G.mk(('arg', 'l2_eps')); ka[208 // 4] = E.G.mk(('arg', 'l2_scale'))
    p64(216, S * S * H * NS); p32(224, L.K)
    if L.lag:
        p64(232, pend.base); p64(240, 2 * L.K * R); p64(248, info.base)
    nz = S // (4 * L.num_warps)
    p32(256, H); p32(260, NS); p32(264, nz)
    p32(268, 32 | (L.num_warps << 16)); p32(272, 1)
    p32(320, 3)
    karg = mem.add(E.Buf('kernarg', next(bases), 128, 'i', ka))
    return mem, karg, bufs

def run(path, fn, L, trace=False):
    name, insts, labels = E.parse_asm(path, fn)
    mem, karg, bufs = build(L)
    w = E.Wave(insts, labels, mem, karg, L.wg, L.tid_y, trace)
    w.run()
    out = {}
    for b in mem.bufs:
        for i, x in b.w.items():
            out[(b.name, i)] = x
    return out, w, bufs

def cone_ops(x, memo=None):
    """distinct float ops in the DAG cone of x"""
    seen = set(); st = [x]; c = Counter()
    while st:
        y = st.pop()
        if not E.is_sym(y) or y.i in seen:
            continue
        seen.add(y.i)
        key = E.G.nodes[y.i]
        c[key[0]] += 1
        for a in key[1:]:
            if E.is_sym(a):
                st.append(a)
    return c

def fmt(x, depth=3):
    if not E.is_sym(x):
        return hex(x)
    k = E.G.nodes[x.i]
    if k[0] == 'ld':
        return f'{k[1]}[{k[2]}]'
    if k[0] == 'arg':
        return k[1]
    if depth == 0:
        return f'%{x.i}'
    args = ', '.join(fmt(a, depth - 1) if (E.is_sym(a) or isinstance(a, int)) and not isinstance(a, bool) else str(a)
                     for a in k[1:])
    return f'{k[0]}({args})'

# ------------------------------------------------------------------ numeric sanity (validates the emulator)
def f32(x):
    try:
        return struct.unpack('<f', struct.pack('<f', x))[0]
    except OverflowError:
        return math.copysign(math.inf, x)
def b2f(b): return struct.unpack('<f', struct.pack('<I', b & E.M32))[0]
def f2b(f): return struct.unpack('<I', struct.pack('<f', f))[0]

class Num:
    def __init__(self, seed=1):
        self.rnd = random.Random(seed); self.leaf = {}; self.memo = {}
    def leafv(self, key):
        if key not in self.leaf:
            name = key[1]
            if name in ('g',):
                v = -abs(self.rnd.gauss(0, 0.3))
            elif name == 'beta':
                v = self.rnd.random()
            elif name == 'scale':
                v = 1 / math.sqrt(S_V)
            elif name == 'l2_eps':
                v = 1e-6
            elif name == 'l2_scale':
                v = 1.0
            else:
                v = self.rnd.gauss(0, 1) * (0.1 if name in ('s0', 'cache', 'pend') else 1)
            self.leaf[key] = f2b(f32(v))
        return self.leaf[key]
    def ev(self, x):
        """bits of x"""
        if not E.is_sym(x):
            return x & E.M32
        if x.i in self.memo:
            return self.memo[x.i]
        k = E.G.nodes[x.i]
        op = k[0]
        F = lambda a: b2f(self.ev(a))
        if op in ('ld', 'arg'):
            r = self.leafv(k)
        elif op == 'neg':
            r = self.ev(k[1]) ^ 0x80000000
        elif op == 'abs':
            r = self.ev(k[1]) & 0x7fffffff
        elif op == 'mul':
            r = f2b(f32(F(k[1]) * F(k[2])))
        elif op == 'add':
            r = f2b(f32(F(k[1]) + F(k[2])))
        elif op == 'fma':
            p = F(k[1]) * F(k[2])
            if k[4]: p = -p
            r = f2b(f32(p + F(k[3])))
        elif op == 'sel':
            r = self.ev(k[2]) if self.ev(k[1]) else self.ev(k[3])
        elif op.startswith('cmp_'):
            a, b = F(k[1]), F(k[2]); c = op[4:]
            un = math.isnan(a) or math.isnan(b)
            r = int({'gt': a > b, 'lt': a < b, 'ge': a >= b, 'le': a <= b, 'eq': a == b,
                     'ngt': not (a > b), 'nlt': not (a < b), 'nge': not (a >= b), 'nle': not (a <= b),
                     'neq': not (a == b), 'lg': a != b and not un, 'u': un, 'o': not un, 'class': 0}[c])
        elif op == 'v_exp_f32':
            a = F(k[1]); r = f2b(f32(2.0 ** a) if a < 128 else math.inf)
        elif op == 'v_rsq_f32':
            a = F(k[1]); r = f2b(f32(1 / math.sqrt(a)) if a > 0 else math.inf)
        elif op == 'v_ldexp_f32':
            e = self.ev(k[2]); e = e - (1 << 32) if e & 0x80000000 else e
            r = f2b(f32(math.ldexp(F(k[1]), e)))
        elif op == 'v_rndne_f32':
            r = f2b(float(round(F(k[1]))))
        elif op == 'v_cvt_i32_f32':
            r = int(F(k[1])) & E.M32
        elif op in ('v_max_f32', 'v_min_f32'):
            r = f2b((max if op == 'v_max_f32' else min)(F(k[1]), F(k[2])))
        else:
            raise RuntimeError(f'numeric: op {op}')
        self.memo[x.i] = r
        return r

def reference(L, num, outs):
    """float64 recurrence for the wave's 4 columns; returns {(buf, idx): value}"""
    S = S_V
    lv = lambda name, i: b2f(num.leafv(('ld', name, i)))
    av = lambda name: b2f(num.leafv(('arg', name)))
    h, seq, z = L.wg
    cols = [(z * L.num_warps + L.tid_y) * 4 + c for c in range(4)]
    iq1 = h % L.neqk1
    if L.gather:
        row = (2 - seq) % L.seq_rows
        sbuf, soff = 'cache', row * S * S * L.H + h * S * S
    else:
        sbuf, soff = 's0', (seq * L.H + h) * S * S
    Sm = {c: [lv(sbuf, soff + c * S + i) for i in range(S)] for c in cols}
    res = {}
    def norm(x):
        ss = sum(t * t for t in x)
        rs = 1 / math.sqrt(ss / S + av('l2_eps'))
        return [av('l2_scale') * rs * t for t in x]
    def step(c, kk, vv, gg, bb):
        s = Sm[c]
        kv = sum(s[i] * kk[i] for i in range(S))
        d = (vv - math.exp(gg) * kv) * bb
        for i in range(S):
            s[i] = math.exp(gg) * s[i] + kk[i] * d
    R = L.H * (2 * S + 2)
    w = 0
    if L.lag:
        rd = 0  # src row 0, read plane 0
        for j in range(L.n_pend):
            base = rd + j * R
            kk = [lv('pend', base + h * S + i) for i in range(S)]
            for c in cols:
                step(c, kk, lv('pend', base + L.H * S + h * S + c), lv('pend', base + 2 * L.H * S + h),
                     lv('pend', base + 2 * L.H * S + L.H + h))
        w = L.n_tokens - min(L.n_tokens, L.K)
        if w == 0:
            for c in cols:
                for i in range(S):
                    res[('state', (seq * L.H + h) * S * S + c * S + i)] = Sm[c][i]
    for t in range(L.n_tokens):
        qo = (seq * L.n_tokens + t) * S * L.neqk1 + iq1 * S
        kk = [lv('k', qo + i) for i in range(S)]; qq = [lv('q', qo + i) for i in range(S)]
        if L.l2:
            kk, qq = norm(kk), norm(qq)
        gb = seq * L.H * L.n_tokens + t * L.H + h
        for c in cols:
            step(c, kk, lv('v', seq * S * L.H * L.n_tokens + t * S * L.H + h * S + c), lv('g', gb), lv('beta', gb))
            res[('dst', (seq * L.n_tokens * L.H + h) * S + t * S * L.H + c)] = av('scale') * sum(
                Sm[c][i] * qq[i] for i in range(S))
        if L.lag and t == w - 1:
            for c in cols:
                for i in range(S):
                    res[('state', (seq * L.H + h) * S * S + c * S + i)] = Sm[c][i]
    if not L.lag:
        for c in cols:
            for i in range(S):
                res[('state', (seq * L.H + h) * S * S + c * S + i)] = Sm[c][i]
    return res

def launches(lag, l2):
    out = []
    for T in (1, 2, 3):
        for gather in (False, True):
            if lag:
                for n_pend, K in ((0, 2), (2, 2), (3, 3)):
                    out.append(Launch(T, lag=True, n_pend=n_pend, K=K, gather=gather, wg=(1, 0, 0), tid_y=0))
                out.append(Launch(T, lag=True, n_pend=1, K=2, gather=gather, wg=(3, 0, 1), tid_y=2, num_warps=4))
            else:
                out.append(Launch(T, gather=gather, wg=(1, 0, 0), tid_y=0))
                out.append(Launch(T, gather=gather, wg=(3, 0, 1), tid_y=3, num_warps=4))
    out.append(Launch(2, n_seqs=2, wg=(2, 1, 0), tid_y=1, num_warps=2, lag=lag, n_pend=1 if lag else 0, K=2))
    # T = 4, 5 and n_pend = 3, 4: the unrolled ping-pong loop followed by both tails; K = 3 < T: mid-loop state write
    for T in (4, 5):
        out.append(Launch(T, wg=(1, 0, 0), tid_y=0, lag=lag, n_pend=3 if lag else 0, K=3 if lag else 1))
        if lag:
            out.append(Launch(T, wg=(1, 0, 0), tid_y=0, lag=True, n_pend=T - 1, K=8))
    for L_ in out:
        L_.l2 = l2
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('base'); ap.add_argument('base_fn'); ap.add_argument('fast', nargs='?'); ap.add_argument('fast_fn', nargs='?')
    ap.add_argument('--lag', action='store_true'); ap.add_argument('--l2', action='store_true')
    ap.add_argument('--numeric', action='store_true'); ap.add_argument('--show', action='store_true')
    ap.add_argument('--trace', action='store_true')
    a = ap.parse_args()
    ok = True
    for L in launches(a.lag, a.l2):
        ob, wb, _ = run(a.base, a.base_fn, L, a.trace)
        desc = f'T={L.n_tokens} seqs={L.n_seqs} lag={L.lag} n_pend={L.n_pend} K={L.K} gather={L.gather} wg={L.wg} y={L.tid_y}/{L.num_warps}'
        if a.numeric:
            num = Num()
            ref = reference(L, num, ob)
            worst = 0.0
            for key, rv in ref.items():
                if key not in ob:
                    print('  MISSING base write', key); ok = False; break
                bv = b2f(num.ev(ob[key]))
                worst = max(worst, abs(bv - rv) / (abs(rv) + 1e-3))
            extra = [k_ for k_ in ob if k_[0] in ('dst', 'state') and k_ not in ref]
            print(f'numeric {desc}: {len(ref)} outputs, max rel err {worst:.2e}, extra writes {len(extra)}')
            if worst > 1e-3 or extra:
                ok = False
        if a.fast:
            of, wf, _ = run(a.fast, a.fast_fn, L)
            same = set(ob) == set(of)
            diff = [k_ for k_ in ob if k_ in of and ob[k_] != of[k_]]
            nd = Counter(k_[0] for k_ in diff)
            print(f'{"OK  " if same and not diff else "DIFF"} {desc}: {len(ob)} words base, {len(of)} fast, '
                  f'{len(diff)} differ {dict(nd)}' + ('' if same else f' write sets differ: '
                  f'{sorted(set(ob) ^ set(of))[:6]}'))
            if diff and a.show:
                k0 = diff[0]
                print('  base', fmt(ob[k0], 4)); print('  fast', fmt(of[k0], 4))
            ok = ok and same and not diff
    if a.fast:
        # per-output float op count of one attn and one state word of the last launch (cone of distinct nodes)
        for key in sorted(ob):
            if key[0] == 'dst':
                print('ops in cone of', key, 'base', dict(cone_ops(ob[key])), 'fast', dict(cone_ops(of[key])))
                break
    print('ALL IDENTICAL' if ok else 'MISMATCH')
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(main())
