#!/usr/bin/env python3
"""isa_kstat.py — per-kernel resource + instruction-mix summary from an AMDGPU .s (clang -S --offload-device-only).

Usage: isa_kstat.py FILE.s [REGEX] [--max N]
Prints per kernel: VGPR, SGPR, static LDS (B), scratch (B), wave32 occupancy bound by VGPR (gfx1100/1101: 1536 VGPR/SIMD lane,
16 waves max, alloc granule 24 — rule verified against compiler '; Occupancy' comments by report 21l), static instruction counts by class:
  vmem loads by width (b32/b64/b96/b128, d16/u8/u16 lumped as 'sub'), lds ops, s_waitcnt, dpp, vopd (v_dual_*),
  wmma, dot (v_dot*), barriers, atomics.
Static counts only (no trip counts). Intended for evidence tables (small excerpts), not vendor binaries.
"""
import re, sys

def occ(vgpr):
    if vgpr <= 0:
        return 16
    g = (vgpr + 23) // 24 * 24
    return min(16, 1536 // g)

CLS = [
    ('ld128', re.compile(r'^\s*(global|buffer|flat)_load_(b128|dwordx4)\b')),
    ('ld96',  re.compile(r'^\s*(global|buffer|flat)_load_(b96|dwordx3)\b')),
    ('ld64',  re.compile(r'^\s*(global|buffer|flat)_load_(b64|dwordx2)\b')),
    ('ld32',  re.compile(r'^\s*(global|buffer|flat)_load_(b32|dword)\b')),
    ('ldsub', re.compile(r'^\s*(global|buffer|flat)_load_(d16|u8|i8|u16|i16|ubyte|sbyte|ushort|sshort)')),
    ('st',    re.compile(r'^\s*(global|buffer|flat)_store_')),
    ('smem',  re.compile(r'^\s*s_(load|buffer_load)_')),
    ('lds',   re.compile(r'^\s*ds_')),
    ('wait',  re.compile(r'^\s*s_waitcnt')),
    ('dpp',   re.compile(r'(row_|quad_perm|row_xmask|dpp8|v_permlane)')),
    ('vopd',  re.compile(r'^\s*v_dual_')),
    ('wmma',  re.compile(r'^\s*v_wmma_')),
    ('dot',   re.compile(r'^\s*v_dot')),
    ('bar',   re.compile(r'^\s*s_barrier')),
    ('atom',  re.compile(r'^\s*(global|buffer|flat|ds)_atomic')),
]

def parse(path):
    meta, bodies, cur = {}, {}, None
    with open(path, errors='replace') as f:
        lines = f.readlines()
    i = 0
    kname = None
    for ln in lines:
        m = re.match(r'^(\S+):\s*(;.*)?$', ln)
        if m and not ln.startswith('.') and not m.group(1).startswith('.'):
            cur = m.group(1)
            bodies.setdefault(cur, {'n': 0})
            continue
        if cur and ln.startswith('.Lfunc_end'):
            cur = None
            continue
        if cur and ln.startswith('\t') and not ln.lstrip().startswith(('.', ';')):
            b = bodies[cur]
            b['n'] += 1
            for k, rx in CLS:
                if rx.search(ln):
                    b[k] = b.get(k, 0) + 1
        m = re.match(r'^\s*\.amdhsa_kernel (\S+)', ln)
        if m:
            kname = m.group(1); meta[kname] = {}
            continue
        if kname:
            m = re.match(r'^\s*\.amdhsa_(next_free_vgpr|next_free_sgpr|group_segment_fixed_size|private_segment_fixed_size)\s+(\d+)', ln)
            if m:
                meta[kname][m.group(1)] = int(m.group(2))
            if '.end_amdhsa_kernel' in ln:
                kname = None
    return meta, bodies

def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    mx = 40
    if '--max' in sys.argv:
        mx = int(sys.argv[sys.argv.index('--max') + 1])
        a = [x for x in a if x != str(mx)]
    path = a[0]
    rx = re.compile(a[1]) if len(a) > 1 else None
    meta, bodies = parse(path)
    cols = ['n', 'ld128', 'ld64', 'ld32', 'ldsub', 'smem', 'lds', 'wait', 'dpp', 'vopd', 'wmma', 'dot', 'bar', 'atom']
    print('vgpr sgpr lds scr occ | ' + ' '.join(cols) + ' | kernel')
    shown = 0
    for k, m in meta.items():
        if rx and not rx.search(k):
            continue
        b = bodies.get(k, {})
        v = m.get('next_free_vgpr', 0)
        print(f"{v:4d} {m.get('next_free_sgpr',0):4d} {m.get('group_segment_fixed_size',0):5d} {m.get('private_segment_fixed_size',0):3d} {occ(v):3d} | "
              + ' '.join(str(b.get(c, 0)) for c in cols) + f' | {k[:150]}')
        shown += 1
        if shown >= mx:
            break

if __name__ == '__main__':
    main()
