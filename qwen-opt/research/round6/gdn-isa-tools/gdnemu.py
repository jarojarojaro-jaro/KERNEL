#!/usr/bin/env python3
"""Symbolic gfx11 wave32 emulator for the gated_delta_net kernels (offline, no GPU).

One wave of one work-group is executed from the compiled assembly (.s from isa.sh). Integer state (addresses, loop
counters, lane ids, masks) is concrete; every float that comes from memory or from a float kernel argument is a
symbolic leaf, and every float instruction builds a hash-consed DAG node. Two kernels compute bit-identical results
for this launch iff every output word they write is the same DAG node (same IEEE operations on the same operands in
the same dependency structure). Canonicalisation is limited to identities that hold bit for bit in IEEE-754 RNE:
  a*b == b*a, a+b == b+a, fma(a,b,c) == fma(b,a,c), a-b == a+(-b), fma(-a,b,c) == fma(a,-b,c), -(a*b) == (-a)*b,
  --x == x
(commutation can only differ in which NaN payload is propagated when both operands are NaN; LLVM itself treats
fadd/fmul/fma multiplicands as commutative, so the base kernel's operand order is not pinned either).
"""
import re, struct, sys, math
from collections import defaultdict

M32 = 0xffffffff
NL = 32  # wave32

# ----------------------------------------------------------------------------------------------- hash-consed DAG
class DAG:
    def __init__(self):
        self.key2id = {}
        self.nodes = []
    def mk(self, key):
        i = self.key2id.get(key)
        if i is None:
            i = len(self.nodes)
            self.nodes.append(key)
            self.key2id[key] = i
        return Sym(i)

class Sym:
    __slots__ = ('i',)
    def __init__(self, i): self.i = i
    def __eq__(self, o): return isinstance(o, Sym) and o.i == self.i
    def __hash__(self): return hash(('S', self.i))
    def __repr__(self): return f'%{self.i}'

G = DAG()

def is_sym(x): return isinstance(x, Sym)

def okey(x):  # orderable key of an operand
    return (1, x.i) if is_sym(x) else (0, x)

def f2b(f): return struct.unpack('<I', struct.pack('<f', f))[0]

def neg(x):
    if not is_sym(x):
        return x ^ 0x80000000
    k = G.nodes[x.i]
    if k[0] == 'neg':
        return k[1]
    return G.mk(('neg', x))

def strip_neg(x):
    if is_sym(x) and G.nodes[x.i][0] == 'neg':
        return G.nodes[x.i][1], True
    if not is_sym(x) and (x & 0x80000000) and x != 0x80000000 and False:
        pass
    return x, False

def fmul(a, b):
    a, na = strip_neg(a); b, nb = strip_neg(b)
    a, b = sorted((a, b), key=okey)
    r = G.mk(('mul', a, b))
    return neg(r) if na ^ nb else r

def fadd(a, b):
    a, b = sorted((a, b), key=okey)
    return G.mk(('add', a, b))

def ffma(a, b, c):
    a, na = strip_neg(a); b, nb = strip_neg(b)
    a, b = sorted((a, b), key=okey)
    return G.mk(('fma', a, b, c, na ^ nb))

def fgen(op, *args):
    return G.mk((op,) + tuple(args))

# ----------------------------------------------------------------------------------------------- masks
class Mask:
    """32 per-lane bits, some symbolic (float compares)."""
    __slots__ = ('bits',)
    def __init__(self, bits): self.bits = tuple(bits)
    def bit(self, l): return self.bits[l]

def mask_bit(m, l):
    if isinstance(m, Mask):
        return m.bits[l]
    if is_sym(m):
        raise RuntimeError('symbolic scalar used as a lane mask')
    return (m >> l) & 1

def mask_norm(bits):
    if all(not is_sym(b) for b in bits):
        v = 0
        for l, b in enumerate(bits):
            v |= (b & 1) << l
        return v
    return Mask(bits)

# ----------------------------------------------------------------------------------------------- parsing
def parse_asm(path, fname_prefix):
    lines = open(path).read().split('\n')
    start = None
    for i, ln in enumerate(lines):
        if ln.startswith(fname_prefix) and ':' in ln:
            start = i
            break
    if start is None:
        raise RuntimeError(f'function {fname_prefix} not found in {path}')
    fname = lines[start].split(':')[0]
    insts = []
    labels = {}
    for ln in lines[start + 1:]:
        if ln.startswith('.Lfunc_end'):
            break
        m = re.match(r'^(\.L\w+):', ln)
        if m:
            labels[m.group(1)] = len(insts)
            continue
        if not ln.startswith('\t') or ln.startswith('\t.') or ln.strip().startswith(';'):
            continue
        s = ln.strip()
        s = re.sub(r'\s;.*$', '', s)
        if not s:
            continue
        insts.append(s)
    return fname, insts, labels

def split_ops(s):
    # mnemonic, operands (comma separated), trailing modifiers (space separated after the last operand)
    parts = s.split(None, 1)
    mn = parts[0]
    if len(parts) == 1:
        return mn, [], {}
    rest = parts[1]
    ops = [o.strip() for o in rest.split(',')]
    mods = {}
    last = ops[-1].split()
    ops[-1] = last[0]
    for t in last[1:]:
        if ':' in t:
            k, v = t.split(':', 1)
            mods[k] = v
        else:
            mods[t] = True
    return mn, ops, mods

def reg_list(o):
    m = re.match(r'^([vs])\[(\d+):(\d+)\]$', o)
    if m:
        return [f'{m.group(1)}{i}' for i in range(int(m.group(2)), int(m.group(3)) + 1)]
    m = re.match(r'^([vs])(\d+)$', o)
    if m:
        return [o]
    if o in ('vcc_lo', 'exec_lo', 'm0', 'null', 'vcc_hi', 'exec_hi'):
        return [o]
    if o == 'vcc':
        return ['vcc_lo', 'vcc_hi']
    if o == 'exec':
        return ['exec_lo', 'exec_hi']
    raise RuntimeError(f'bad reg {o}')

INLINE_F = {'0.5': 0x3f000000, '-0.5': 0xbf000000, '1.0': 0x3f800000, '-1.0': 0xbf800000, '2.0': 0x40000000,
            '-2.0': 0xc0000000, '4.0': 0x40800000, '-4.0': 0xc0800000, '0.15915494': 0x3e22f983}

# ----------------------------------------------------------------------------------------------- memory
class Buf:
    def __init__(self, name, base, nwords, kind, init=None):
        self.name, self.base, self.nwords, self.kind = name, base, nwords, kind  # kind: 'f' symbolic float, 'i' int
        self.init = init or {}
        self.w = {}

class Mem:
    def __init__(self):
        self.bufs = []
        self.writes = []  # (buf, idx, value) in program order
    def add(self, b): self.bufs.append(b); return b
    def find(self, addr):
        for b in self.bufs:
            if b.base <= addr < b.base + 4 * b.nwords:
                off = addr - b.base
                if off % 4:
                    raise RuntimeError(f'unaligned {hex(addr)} in {b.name}')
                return b, off // 4
        raise RuntimeError(f'address {hex(addr)} outside every buffer')
    def load(self, addr):
        b, i = self.find(addr)
        if i in b.w:
            return b.w[i]
        if b.kind == 'i':
            v = b.init.get(i, 0)
            return v if is_sym(v) else v & M32
        return G.mk(('ld', b.name, i))
    def store(self, addr, v):
        b, i = self.find(addr)
        b.w[i] = v
        self.writes.append((b.name, i, v))

# ----------------------------------------------------------------------------------------------- the wave
class Wave:
    def __init__(self, insts, labels, mem, kernarg, wg_id, tid_y, trace=False):
        self.insts, self.labels, self.mem, self.kernarg = insts, labels, mem, kernarg
        self.v = defaultdict(lambda: [0] * NL)
        self.s = defaultdict(int)
        self.scc = 0
        self.lds = {}
        self.trace = trace
        self.counts = defaultdict(int)
        self.s['s0'] = kernarg.base & M32
        self.s['s1'] = kernarg.base >> 32
        self.s['s13'], self.s['s14'], self.s['s15'] = wg_id
        self.s['exec_lo'] = M32
        self.s['exec_hi'] = 0
        self.v['v0'] = [l | (tid_y << 10) for l in range(NL)]

    # --- operand access
    def sget(self, o):
        if o == 'scc':
            return self.scc
        if o in ('null',):
            return 0
        if re.match(r'^-?\d+$', o):
            return int(o) & M32
        if o.startswith('0x'):
            return int(o, 16) & M32
        if o in INLINE_F:
            return INLINE_F[o]
        return self.s[o]

    def sget64(self, o):
        r = reg_list(o) if not (re.match(r'^-?\d+$', o) or o.startswith('0x')) else None
        if r is None:
            v = int(o, 0)
            return v & 0xffffffffffffffff
        if len(r) == 1:
            return self.sget(r[0])
        lo, hi = self.sget(r[0]), self.sget(r[1])
        if is_sym(lo) or is_sym(hi) or isinstance(lo, Mask) or isinstance(hi, Mask):
            raise RuntimeError(f'symbolic 64-bit scalar {o}')
        return lo | (hi << 32)

    def sset(self, o, v):
        if o == 'null':
            return
        self.s[o] = v if (is_sym(v) or isinstance(v, Mask)) else v & M32

    def sset64(self, o, v):
        r = reg_list(o)
        self.s[r[0]] = v & M32
        self.s[r[1]] = (v >> 32) & M32

    def lane_src(self, o, l, f32=False):
        """value of operand o in lane l (VALU source)"""
        negf = absf = False
        if o.startswith('-') and not re.match(r'^-\d', o) and not re.match(r'^-0x', o):
            negf, o = True, o[1:]
        if o.startswith('|') and o.endswith('|'):
            absf, o = True, o[1:-1]
        if o.startswith('-') and o[1:] in INLINE_F:
            pass
        if o.startswith('v') and re.match(r'^v\d+$', o):
            x = self.v[o][l]
        elif re.match(r'^-?\d+$', o):
            x = int(o) & M32
        elif o.startswith('0x'):
            x = int(o, 16) & M32
        elif o in INLINE_F:
            x = INLINE_F[o]
        else:
            x = self.s[o] if o != 'scc' else self.scc
            if isinstance(x, Mask):
                raise RuntimeError(f'lane mask {o} used as a VALU value')
        if absf:
            x = G.mk(('abs', x)) if is_sym(x) else x & 0x7fffffff
        if negf:
            x = neg(x)
        return x

    def exec_bits(self):
        e = self.s['exec_lo']
        if isinstance(e, Mask) or is_sym(e):
            raise RuntimeError('symbolic exec')
        return e

    def vwrite(self, o, vals):
        e = self.exec_bits()
        regs = reg_list(o)
        if len(regs) == 1:
            r = self.v[o]
            for l in range(NL):
                if (e >> l) & 1:
                    r[l] = vals[l]
        else:  # 64-bit values per lane (python ints) or pairs
            lo, hi = self.v[regs[0]], self.v[regs[1]]
            for l in range(NL):
                if (e >> l) & 1:
                    x = vals[l]
                    if isinstance(x, tuple):
                        lo[l], hi[l] = x
                    else:
                        lo[l], hi[l] = x & M32, (x >> 32) & M32
        self.v[regs[0]] = self.v[regs[0]]

    def lane64(self, o, l):
        regs = reg_list(o) if not (re.match(r'^-?\d+$', o) or o.startswith('0x')) else None
        if regs is None:
            v = int(o, 0)
            return v & 0xffffffffffffffff if v >= 0 else (v + (1 << 64))
        if len(regs) == 1:
            x = self.lane_src(o, l)
            return x
        a = self.v[regs[0]][l] if regs[0].startswith('v') else self.s[regs[0]]
        b = self.v[regs[1]][l] if regs[1].startswith('v') else self.s[regs[1]]
        if is_sym(a) or is_sym(b):
            raise RuntimeError(f'symbolic 64-bit lane value {o}')
        return a | (b << 32)

    # --- run
    def run(self, max_steps=2_000_000):
        pc = 0
        steps = 0
        while True:
            steps += 1
            if steps > max_steps:
                raise RuntimeError('step limit')
            s = self.insts[pc]
            if self.trace:
                print(f'{pc:5d} {s}')
            npc = self.step(s, pc)
            if npc == -1:
                return
            pc = npc

    def step(self, s, pc):
        if '::' in s:
            a, b = [x.strip() for x in s.split('::')]
            self.counts['v_dual'] += 1
            for half in (a, b):
                self.counts['vopd.' + half.split()[0].replace('v_dual_', 'v_')] += 1
            ra = self.valu(a, defer=True)
            rb = self.valu(b, defer=True)
            for dst, vals in (ra, rb):
                self.vwrite(dst, vals)
            return pc + 1
        mn, ops, mods = split_ops(s)
        base = re.sub(r'_e(32|64)$', '', mn)
        self.counts[base] += 1
        if base in ('s_waitcnt', 's_delay_alu', 's_clause', 's_waitcnt_depctr', 's_nop', 's_waitcnt_vscnt',
                    's_waitcnt_vmcnt', 's_waitcnt_lgkmcnt', 's_sendmsg', 's_set_inst_prefetch_distance',
                    's_inst_prefetch', 's_barrier', 's_waitcnt_expcnt'):
            return pc + 1
        if base == 's_endpgm':
            return -1
        if base == 's_branch':
            return self.labels[ops[0]]
        if base.startswith('s_cbranch_'):
            c = base[len('s_cbranch_'):]
            if c == 'scc0': t = self.scc == 0
            elif c == 'scc1': t = self.scc == 1
            elif c == 'vccz': t = self.sget('vcc_lo') == 0
            elif c == 'vccnz': t = self.sget('vcc_lo') != 0
            elif c == 'execz': t = self.exec_bits() == 0
            elif c == 'execnz': t = self.exec_bits() != 0
            else: raise RuntimeError(s)
            if isinstance(self.sget('vcc_lo'), Mask) and c.startswith('vcc'):
                raise RuntimeError('branch on symbolic vcc')
            return self.labels[ops[0]] if t else pc + 1
        if base.startswith('s_load_'):
            self.sload(base, ops)
            return pc + 1
        if base.startswith('s_'):
            self.salu(base, ops, s)
            return pc + 1
        if base.startswith('global_load') or base.startswith('global_store'):
            self.gmem(base, ops, mods)
            return pc + 1
        if base.startswith('ds_'):
            self.ds(base, ops, mods)
            return pc + 1
        if base.startswith('v_'):
            r = self.valu(s)
            if r is not None:
                dst, vals = r
                self.vwrite(dst, vals)
            return pc + 1
        raise RuntimeError(f'unhandled {s}')

    # --- scalar memory
    def sload(self, base, ops):
        n = {'s_load_b32': 1, 's_load_b64': 2, 's_load_b96': 3, 's_load_b128': 4, 's_load_b256': 8,
             's_load_b512': 16}[base]
        dst = reg_list(ops[0])
        addr = self.sget64(ops[1])
        off = ops[2]
        offv = int(off, 0) if re.match(r'^(0x[0-9a-f]+|\d+)$', off) else self.sget(off)
        addr += offv
        for i in range(n):
            self.s[dst[i]] = self.mem.load(addr + 4 * i)

    # --- SALU
    def salu(self, base, ops, s):
        op = base
        g = self.sget
        def u(x):
            if is_sym(x) or isinstance(x, Mask):
                raise RuntimeError(f'symbolic SALU operand in {s}')
            return x & M32
        def i32(x):
            x = u(x)
            return x - (1 << 32) if x & 0x80000000 else x
        if op in ('s_mov_b32', 's_movk_i32'):
            v = g(ops[1]) if not ops[1].startswith('0x') else int(ops[1], 16) & M32
            self.sset(ops[0], v); return
        if op == 's_mov_b64':
            src = ops[1]
            if src.startswith('s[') or src in ('vcc', 'exec'):
                r = reg_list(src); d = reg_list(ops[0])
                self.s[d[0]], self.s[d[1]] = self.s[r[0]], self.s[r[1]]
            else:
                v = int(src, 0) & 0xffffffffffffffff
                self.sset64(ops[0], v)
            return
        if op == 's_add_u32':
            r = u(g(ops[1])) + u(g(ops[2])); self.scc = r >> 32; self.sset(ops[0], r); return
        if op == 's_addc_u32':
            r = u(g(ops[1])) + u(g(ops[2])) + self.scc; self.scc = r >> 32; self.sset(ops[0], r); return
        if op == 's_sub_u32':
            a, b = u(g(ops[1])), u(g(ops[2])); self.scc = int(b > a); self.sset(ops[0], a - b); return
        if op == 's_subb_u32':
            a, b = u(g(ops[1])), u(g(ops[2])); r = a - b - self.scc; self.scc = int(r < 0); self.sset(ops[0], r); return
        if op == 's_add_i32':
            a, b = i32(g(ops[1])), i32(g(ops[2])); r = a + b
            self.scc = int(r > 0x7fffffff or r < -0x80000000); self.sset(ops[0], r); return
        if op == 's_sub_i32':
            a, b = i32(g(ops[1])), i32(g(ops[2])); r = a - b
            self.scc = int(r > 0x7fffffff or r < -0x80000000); self.sset(ops[0], r); return
        if op == 's_mul_i32':
            self.sset(ops[0], u(g(ops[1])) * u(g(ops[2]))); return
        if op == 's_mul_hi_u32':
            self.sset(ops[0], (u(g(ops[1])) * u(g(ops[2]))) >> 32); return
        if op == 's_mul_hi_i32':
            self.sset(ops[0], (i32(g(ops[1])) * i32(g(ops[2]))) >> 32); return
        if op in ('s_lshl_b32', 's_lshr_b32', 's_ashr_i32'):
            a, b = u(g(ops[1])), u(g(ops[2])) & 31
            r = (a << b) if op == 's_lshl_b32' else (a >> b) if op == 's_lshr_b32' else (i32(a) >> b)
            r &= M32; self.scc = int(r != 0); self.sset(ops[0], r); return
        m = re.match(r's_lshl([1-4])_add_u32', op)
        if m:
            r = (u(g(ops[1])) << int(m.group(1))) + u(g(ops[2])); self.scc = int(r >> 32 != 0); self.sset(ops[0], r); return
        if op in ('s_lshl_b64', 's_lshr_b64', 's_ashr_i64'):
            a = self.sget64(ops[1]); b = u(g(ops[2])) & 63
            if op == 's_lshl_b64': r = (a << b) & 0xffffffffffffffff
            elif op == 's_lshr_b64': r = a >> b
            else:
                sa = a - (1 << 64) if a >> 63 else a
                r = (sa >> b) & 0xffffffffffffffff
            self.scc = int(r != 0); self.sset64(ops[0], r); return
        if op in ('s_and_b32', 's_or_b32', 's_xor_b32', 's_and_not1_b32', 's_or_not1_b32', 's_andn2_b32',
                  's_orn2_b32', 's_nand_b32', 's_nor_b32', 's_xnor_b32'):
            a, b = u(g(ops[1])), u(g(ops[2]))
            r = {'s_and_b32': a & b, 's_or_b32': a | b, 's_xor_b32': a ^ b, 's_and_not1_b32': a & ~b,
                 's_andn2_b32': a & ~b, 's_or_not1_b32': a | (~b & M32), 's_orn2_b32': a | (~b & M32),
                 's_nand_b32': ~(a & b), 's_nor_b32': ~(a | b), 's_xnor_b32': ~(a ^ b)}[op] & M32
            self.scc = int(r != 0); self.sset(ops[0], r); return
        if op in ('s_and_b64', 's_or_b64', 's_xor_b64', 's_and_not1_b64', 's_andn2_b64'):
            a, b = self.sget64(ops[1]), self.sget64(ops[2])
            r = {'s_and_b64': a & b, 's_or_b64': a | b, 's_xor_b64': a ^ b, 's_and_not1_b64': a & ~b,
                 's_andn2_b64': a & ~b}[op] & 0xffffffffffffffff
            self.scc = int(r != 0); self.sset64(ops[0], r); return
        if op == 's_not_b32':
            r = ~u(g(ops[1])) & M32; self.scc = int(r != 0); self.sset(ops[0], r); return
        if op in ('s_and_saveexec_b32', 's_or_saveexec_b32', 's_and_not1_saveexec_b32', 's_andn2_saveexec_b32'):
            e = self.exec_bits(); m = u(g(ops[1]))
            self.sset(ops[0], e)
            ne = {'s_and_saveexec_b32': m & e, 's_or_saveexec_b32': m | e,
                  's_and_not1_saveexec_b32': m & ~e, 's_andn2_saveexec_b32': m & ~e}[op] & M32
            self.s['exec_lo'] = ne; self.scc = int(ne != 0); return
        if op == 's_cselect_b32':
            self.sset(ops[0], g(ops[1]) if self.scc else g(ops[2])); return
        if op == 's_cselect_b64':
            a = self.sget64(ops[1]); b = self.sget64(ops[2]); self.sset64(ops[0], a if self.scc else b); return
        m = re.match(r's_cmp_(eq|lg|lt|le|gt|ge)_(i32|u32|u64)', op)
        if m:
            c, t = m.groups()
            if t == 'u64':
                a, b = self.sget64(ops[0]), self.sget64(ops[1])
            elif t == 'i32':
                a, b = i32(g(ops[0])), i32(g(ops[1]))
            else:
                a, b = u(g(ops[0])), u(g(ops[1]))
            self.scc = int({'eq': a == b, 'lg': a != b, 'lt': a < b, 'le': a <= b, 'gt': a > b, 'ge': a >= b}[c])
            return
        if op in ('s_min_i32', 's_max_i32'):
            a, b = i32(g(ops[1])), i32(g(ops[2])); r = min(a, b) if op == 's_min_i32' else max(a, b)
            self.scc = int((a < b) if op == 's_min_i32' else (a > b)); self.sset(ops[0], r); return
        if op in ('s_min_u32', 's_max_u32'):
            a, b = u(g(ops[1])), u(g(ops[2])); r = min(a, b) if op == 's_min_u32' else max(a, b)
            self.scc = int((a < b) if op == 's_min_u32' else (a > b)); self.sset(ops[0], r); return
        if op in ('s_bfe_u32', 's_bfe_i32'):
            a, b = u(g(ops[1])), u(g(ops[2])); off, w = b & 31, (b >> 16) & 0x7f
            r = (a >> off) & ((1 << w) - 1) if w else 0
            if op == 's_bfe_i32' and w and (r >> (w - 1)) & 1:
                r -= (1 << w)
            self.scc = int((r & M32) != 0); self.sset(ops[0], r); return
        if op == 's_abs_i32':
            r = abs(i32(g(ops[1]))); self.scc = int(r != 0); self.sset(ops[0], r); return
        if op == 's_sext_i32_i16':
            a = u(g(ops[1])) & 0xffff; self.sset(ops[0], a - 0x10000 if a & 0x8000 else a); return
        if op in ('s_addk_i32', 's_mulk_i32'):
            k = int(ops[1], 0) & 0xffff
            k = k - 0x10000 if k & 0x8000 else k
            a = i32(g(ops[0]))
            r = a + k if op == 's_addk_i32' else a * k
            if op == 's_addk_i32':
                self.scc = int(r > 0x7fffffff or r < -0x80000000)
            self.sset(ops[0], r); return
        raise RuntimeError(f'unhandled SALU {s}')

    # --- global memory
    def gmem(self, base, ops, mods):
        e = self.exec_bits()
        off = int(mods.get('offset', '0'), 0)
        isload = base.startswith('global_load')
        width = {'b32': 1, 'b64': 2, 'b96': 3, 'b128': 4}[base.split('_')[-1]]
        if isload:
            dst, vaddr, saddr = ops[0], ops[1], ops[2]
        else:
            vaddr, data, saddr = ops[0], ops[1], ops[2]
        if isload:
            regs = reg_list(dst)
            assert len(regs) == width
            res = [[None] * NL for _ in range(width)]
        else:
            dregs = reg_list(data)
        for l in range(NL):
            if not (e >> l) & 1:
                continue
            if saddr == 'off':
                a = self.lane64(vaddr, l)
            else:
                vo = self.v[vaddr][l]
                if is_sym(vo):
                    raise RuntimeError('symbolic address')
                a = self.sget64(saddr) + vo
            a = (a + off) & 0xffffffffffffffff
            for j in range(width):
                if isload:
                    res[j][l] = self.mem.load(a + 4 * j)
                else:
                    self.mem.store(a + 4 * j, self.v[dregs[j]][l])
        if isload:
            for j in range(width):
                r = self.v[regs[j]]
                for l in range(NL):
                    if (e >> l) & 1:
                        r[l] = res[j][l]

    # --- LDS
    def ds(self, base, ops, mods):
        e = self.exec_bits()
        off = int(mods.get('offset', '0'), 0)
        if base == 'ds_bpermute_b32':
            dst, addr, data = ops
            src = list(self.v[data])
            out = [None] * NL
            for l in range(NL):
                if (e >> l) & 1:
                    a = self.v[addr][l]
                    if is_sym(a):
                        raise RuntimeError('symbolic bpermute address')
                    out[l] = src[((a + off) >> 2) & (NL - 1)]
            self.vwrite(dst, out)
            return
        m = re.match(r'ds_(store|load)_(b32|b64|b96|b128)$', base)
        if m:
            kind, w = m.group(1), {'b32': 1, 'b64': 2, 'b96': 3, 'b128': 4}[m.group(2)]
            if kind == 'store':
                addr, data = ops
                dregs = reg_list(data)
                for l in range(NL):
                    if (e >> l) & 1:
                        a = self.v[addr][l] + off
                        for j in range(w):
                            self.lds[a + 4 * j] = self.v[dregs[j]][l]
            else:
                dst, addr = ops
                regs = reg_list(dst)
                res = [[None] * NL for _ in range(w)]
                for l in range(NL):
                    if (e >> l) & 1:
                        a = self.v[addr][l] + off
                        for j in range(w):
                            if a + 4 * j not in self.lds:
                                raise RuntimeError(f'LDS read of unwritten {a + 4 * j}')
                            res[j][l] = self.lds[a + 4 * j]
                for j in range(w):
                    r = self.v[regs[j]]
                    for l in range(NL):
                        if (e >> l) & 1:
                            r[l] = res[j][l]
            return
        m = re.match(r'ds_(store|load)_2addr_(stride64_)?(b32|b64)$', base)
        if m:
            kind, st, w = m.group(1), m.group(2), {'b32': 1, 'b64': 2}[m.group(3)]
            unit = 4 * w * (64 if st else 1)
            o0, o1 = int(mods.get('offset0', '0'), 0) * unit, int(mods.get('offset1', '0'), 0) * unit
            if kind == 'store':
                addr, d0, d1 = ops
                r0, r1 = reg_list(d0), reg_list(d1)
                for l in range(NL):
                    if (e >> l) & 1:
                        a = self.v[addr][l]
                        for j in range(w):
                            self.lds[a + o0 + 4 * j] = self.v[r0[j]][l]
                            self.lds[a + o1 + 4 * j] = self.v[r1[j]][l]
            else:
                dst, addr = ops
                regs = reg_list(dst)
                res = [[None] * NL for _ in range(2 * w)]
                for l in range(NL):
                    if (e >> l) & 1:
                        a = self.v[addr][l]
                        for j in range(w):
                            res[j][l] = self.lds[a + o0 + 4 * j]
                            res[w + j][l] = self.lds[a + o1 + 4 * j]
                for j in range(2 * w):
                    r = self.v[regs[j]]
                    for l in range(NL):
                        if (e >> l) & 1:
                            r[l] = res[j][l]
            return
        raise RuntimeError(f'unhandled DS {base}')

    # --- VALU
    def dpp_src(self, o, mods):
        """per-lane src0 after the DPP lane move"""
        if self.exec_bits() != M32:
            raise RuntimeError('DPP with inactive lanes is not modelled (source lanes could be disabled)')
        vals = [self.lane_src(o, l) for l in range(NL)]
        rm = int(mods.get('row_mask', '0xf'), 0); bm = int(mods.get('bank_mask', '0xf'), 0)
        if rm != 0xf or bm != 0xf:
            raise RuntimeError('partial DPP masks not modelled')
        out = [None] * NL
        for l in range(NL):
            row, i = l & ~15, l & 15
            if 'row_xmask' in mods:
                j = row | (i ^ int(mods['row_xmask'], 0))
            elif 'row_shr' in mods:
                k = int(mods['row_shr'], 0); j = row | (i - k) if i - k >= 0 else None
            elif 'row_shl' in mods:
                k = int(mods['row_shl'], 0); j = row | (i + k) if i + k < 16 else None
            elif 'row_ror' in mods:
                j = row | ((i - int(mods['row_ror'], 0)) & 15)
            elif 'row_mirror' in mods:
                j = row | (15 - i)
            elif 'row_half_mirror' in mods:
                j = row | ((i & 8) | (7 - (i & 7)))
            elif 'row_share' in mods:
                j = row | int(mods['row_share'], 0)
            elif 'quad_perm' in mods:
                qp = [int(x) for x in mods['quad_perm'].strip('[]').split(',')]
                j = (l & ~3) | qp[l & 3]
            else:
                raise RuntimeError(f'DPP control not modelled: {mods}')
            if j is None:
                raise RuntimeError('DPP out-of-row source not modelled')
            out[l] = vals[j]
        return out

    def valu(self, s, defer=False):
        mn, ops, mods = split_ops(s)
        dpp = mn.endswith('_dpp')
        mn = re.sub(r'_(e32|e64|dpp)$', '', mn)
        mn = mn.replace('v_dual_', 'v_')
        if 'clamp' in mods or 'mul' in mods or 'div' in mods:
            raise RuntimeError(f'output modifier not modelled: {s}')
        e = self.exec_bits()
        L = range(NL)

        def src(i):
            if i == 0 and dpp:
                return self.dpp_src(ops[1], mods)
            return [self.lane_src(ops[1 + i], l) for l in L]

        def conc(*xs): return all(not is_sym(x) for x in xs)

        def i32(x): return x - (1 << 32) if x & 0x80000000 else x

        def ls(o, l):
            return self.lane_src(o, l) if (e >> l) & 1 else 0

        def l64(o, l):
            return self.lane64(o, l) if (e >> l) & 1 else 0

        out = None
        dst = ops[0] if ops else None
        if mn in ('v_readfirstlane_b32', 'v_readlane_b32'):
            if mn == 'v_readlane_b32':
                ln = self.sget(ops[2])
            else:
                ln = next((l for l in L if (e >> l) & 1), 0)
            self.sset(ops[0], self.lane_src(ops[1], ln))
            return None
        if mn in ('v_mov_b32',):
            out = src(0)
        elif mn == 'v_mul_f32':
            a, b = src(0), src(1); out = [fmul(a[l], b[l]) for l in L]
        elif mn == 'v_add_f32':
            a, b = src(0), src(1); out = [fadd(a[l], b[l]) for l in L]
        elif mn == 'v_sub_f32':
            a, b = src(0), src(1); out = [fadd(a[l], neg(b[l])) for l in L]
        elif mn == 'v_subrev_f32':
            a, b = src(0), src(1); out = [fadd(b[l], neg(a[l])) for l in L]
        elif mn == 'v_fma_f32':
            a, b, c = src(0), src(1), src(2); out = [ffma(a[l], b[l], c[l]) for l in L]
        elif mn == 'v_fmac_f32':
            a, b = src(0), src(1); d = list(self.v[dst]); out = [ffma(a[l], b[l], d[l]) for l in L]
        elif mn == 'v_fmaak_f32':
            a, b, k = src(0), src(1), src(2); out = [ffma(a[l], b[l], k[l]) for l in L]
        elif mn == 'v_fmamk_f32':
            a, k, b = src(0), src(1), src(2); out = [ffma(a[l], k[l], b[l]) for l in L]
        elif mn == 'v_cndmask_b32':
            a, b = src(0), src(1)
            m = self.s['vcc_lo'] if len(ops) == 3 else self.sget(ops[3])
            out = []
            for l in L:
                bit = mask_bit(m, l)
                if is_sym(bit):
                    out.append(G.mk(('sel', bit, b[l], a[l])))
                else:
                    out.append(b[l] if bit else a[l])
        elif mn.startswith('v_cmp_') or mn.startswith('v_cmpx_'):
            mm = re.match(r'v_cmpx?_(\w+?)_([uif])(16|32|64)$', mn)
            c, t, w = mm.group(1), mm.group(2), int(mm.group(3))
            if len(ops) == 2:
                sd, o0, o1 = 'vcc_lo', ops[0], ops[1]
            else:
                sd, o0, o1 = ops[0], ops[1], ops[2]
            bits = [0] * NL
            for l in L:
                if not (e >> l) & 1:
                    continue
                if w == 64:
                    a, b = self.lane64(o0, l), self.lane64(o1, l)
                else:
                    a, b = self.lane_src(o0, l), self.lane_src(o1, l)
                if t == 'f' or not conc(a, b):
                    if t != 'f':
                        raise RuntimeError(f'symbolic int compare {s}')
                    bits[l] = G.mk(('cmp_' + c, a, b))
                    continue
                if t == 'i':
                    a = a - (1 << w) if a >> (w - 1) else a
                    b = b - (1 << w) if b >> (w - 1) else b
                bits[l] = int({'eq': a == b, 'ne': a != b, 'lg': a != b, 'lt': a < b, 'le': a <= b,
                               'gt': a > b, 'ge': a >= b}[c])
            v = mask_norm(bits)
            if mn.startswith('v_cmpx_'):
                self.s['exec_lo'] = v
            else:
                self.sset(sd, v)
            return None
        elif mn == 'v_mbcnt_lo_u32_b32':
            a, b = src(0), src(1); out = [bin(a[l] & ((1 << l) - 1)).count('1') + b[l] for l in L]
        elif mn == 'v_mbcnt_hi_u32_b32':
            a, b = src(0), src(1); out = [b[l] for l in L]
        elif mn in ('v_add_co_u32', 'v_sub_co_u32', 'v_subrev_co_u32'):
            sd = ops[1]
            a = [ls(ops[2], l) for l in L]; b = [ls(ops[3], l) for l in L]
            bits = [0] * NL; out = [0] * NL
            for l in L:
                if mn == 'v_add_co_u32':
                    r = a[l] + b[l]; bits[l] = int(r >> 32 != 0)
                elif mn == 'v_sub_co_u32':
                    r = a[l] - b[l]; bits[l] = int(r < 0)
                else:
                    r = b[l] - a[l]; bits[l] = int(r < 0)
                out[l] = r & M32
            for l in L:
                if not (e >> l) & 1:
                    bits[l] = 0
            self.sset(sd, mask_norm(bits))
        elif mn in ('v_add_co_ci_u32', 'v_sub_co_ci_u32', 'v_subrev_co_ci_u32'):
            sd = ops[1]
            a = [ls(ops[2], l) for l in L]; b = [ls(ops[3], l) for l in L]
            cin = self.sget(ops[4]) if len(ops) > 4 else self.s['vcc_lo']
            bits = [0] * NL; out = [0] * NL
            for l in L:
                c = mask_bit(cin, l)
                if mn == 'v_add_co_ci_u32':
                    r = a[l] + b[l] + c; bits[l] = int(r >> 32 != 0)
                elif mn == 'v_sub_co_ci_u32':
                    r = a[l] - b[l] - c; bits[l] = int(r < 0)
                else:
                    r = b[l] - a[l] - c; bits[l] = int(r < 0)
                out[l] = r & M32
            self.sset(sd, mask_norm(bits))
        elif mn == 'v_mad_u64_u32':
            a = [ls(ops[2], l) for l in L]; b = [ls(ops[3], l) for l in L]
            c = [l64(ops[4], l) for l in L]
            out = [(a[l] * b[l] + c[l]) & 0xffffffffffffffff for l in L]
            self.sset(ops[1], 0)
        elif mn == 'v_lshlrev_b64':
            sh = [ls(ops[1], l) for l in L]; x = [l64(ops[2], l) for l in L]
            out = [(x[l] << (sh[l] & 63)) & 0xffffffffffffffff for l in L]
        elif mn == 'v_lshrrev_b64':
            sh = [ls(ops[1], l) for l in L]; x = [l64(ops[2], l) for l in L]
            out = [x[l] >> (sh[l] & 63) for l in L]
        elif mn == 'v_ashrrev_i64':
            sh = [ls(ops[1], l) for l in L]; x = [l64(ops[2], l) for l in L]
            out = [((x[l] - (1 << 64) if x[l] >> 63 else x[l]) >> (sh[l] & 63)) & 0xffffffffffffffff for l in L]
        else:
            nsrc = len(ops) - 1
            srcs = [src(i) for i in range(nsrc)]
            out = []
            for l in L:
                xs = [sv[l] for sv in srcs]
                if conc(*xs):
                    r = self.int_valu(mn, xs, s)
                    if r is None:
                        r = fgen(mn, *xs)
                else:
                    r = fgen(mn, *xs)
                out.append(r)
        if defer:
            return dst, out
        return dst, out

    def int_valu(self, mn, x, s):
        def i32(v): return v - (1 << 32) if v & 0x80000000 else v
        if mn == 'v_add_nc_u32': return (x[0] + x[1]) & M32
        if mn == 'v_sub_nc_u32': return (x[0] - x[1]) & M32
        if mn == 'v_subrev_nc_u32': return (x[1] - x[0]) & M32
        if mn == 'v_and_b32': return x[0] & x[1]
        if mn == 'v_or_b32': return x[0] | x[1]
        if mn == 'v_xor_b32': return x[0] ^ x[1]
        if mn == 'v_not_b32': return ~x[0] & M32
        if mn == 'v_lshlrev_b32': return (x[1] << (x[0] & 31)) & M32
        if mn == 'v_lshrrev_b32': return x[1] >> (x[0] & 31)
        if mn == 'v_ashrrev_i32': return (i32(x[1]) >> (x[0] & 31)) & M32
        if mn == 'v_bfe_u32':
            off, w = x[1] & 31, x[2] & 31
            return (x[0] >> off) & ((1 << w) - 1)
        if mn == 'v_bfe_i32':
            off, w = x[1] & 31, x[2] & 31
            r = (x[0] >> off) & ((1 << w) - 1)
            if w and (r >> (w - 1)) & 1: r -= 1 << w
            return r & M32
        if mn == 'v_lshl_add_u32': return ((x[0] << (x[1] & 31)) + x[2]) & M32
        if mn == 'v_add_lshl_u32': return ((x[0] + x[1]) << (x[2] & 31)) & M32
        if mn == 'v_lshl_or_b32': return ((x[0] << (x[1] & 31)) | x[2]) & M32
        if mn == 'v_and_or_b32': return (x[0] & x[1]) | x[2]
        if mn == 'v_or3_b32': return x[0] | x[1] | x[2]
        if mn == 'v_xad_u32': return ((x[0] ^ x[1]) + x[2]) & M32
        if mn == 'v_add3_u32': return (x[0] + x[1] + x[2]) & M32
        if mn == 'v_mul_lo_u32': return (x[0] * x[1]) & M32
        if mn == 'v_mul_hi_u32': return (x[0] * x[1]) >> 32
        if mn == 'v_mul_u32_u24': return ((x[0] & 0xffffff) * (x[1] & 0xffffff)) & M32
        if mn == 'v_mad_u32_u24': return ((x[0] & 0xffffff) * (x[1] & 0xffffff) + x[2]) & M32
        if mn == 'v_min_u32': return min(x[0], x[1])
        if mn == 'v_max_u32': return max(x[0], x[1])
        if mn == 'v_min_i32': return min(i32(x[0]), i32(x[1])) & M32
        if mn == 'v_max_i32': return max(i32(x[0]), i32(x[1])) & M32
        if mn == 'v_readfirstlane_b32': return x[0]
        return None
