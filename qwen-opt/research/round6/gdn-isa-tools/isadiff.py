#!/usr/bin/env python3
"""isadiff.py BASE.s NEW.s: every kernel of BASE.s must be byte-identical in NEW.s (code, .amdhsa_kernel descriptor
and metadata), after renaming the per-module function index in local labels (.LBB<fn>_<bb>, .Lfunc_end<fn>, ...)."""
import re, sys

def kernels(path):
    txt = open(path).read()
    lines = txt.split('\n')
    code, desc = {}, {}
    i = 0
    while i < len(lines):
        m = re.match(r'^(_Z\S+):\s', lines[i])
        if m:
            name = m.group(1); j = i
            while not lines[j].startswith('.Lfunc_end'):
                j += 1
            code[name] = lines[i:j + 1]
            i = j
        m = re.match(r'^\s*\.amdhsa_kernel (\S+)', lines[i])
        if m:
            name = m.group(1); j = i
            while '.end_amdhsa_kernel' not in lines[j]:
                j += 1
            desc[name] = lines[i:j + 1]
            i = j
        i += 1
    meta = {}
    mtxt = txt[txt.index('amdhsa.kernels:'):]
    for blk in re.split(r'\n  - \.args:', mtxt)[1:]:
        m = re.search(r'\.name:\s+(\S+)', blk)
        meta[m.group(1)] = blk.split('\namdhsa.target')[0]
    return code, desc, meta

def norm(ls):
    out = []
    for l in ls:
        l = re.sub(r'\s*;.*$', '', l)  # comments (their column depends on the width of renumbered labels)
        l = re.sub(r'BB\d+_', 'BB_', l)
        l = re.sub(r'\.Lfunc_end\d+', '.Lfunc_end', l)
        l = re.sub(r'\.Ltmp\d+', '.Ltmp', l)
        out.append(l)
    return out

def main():
    cb, db, mb = kernels(sys.argv[1])
    cn, dn, mn = kernels(sys.argv[2])
    bad = 0
    for name in cb:
        ok = name in cn and norm(cb[name]) == norm(cn[name]) and norm(db[name]) == norm(dn.get(name, [])) and mb[name] == mn.get(name)
        if not ok:
            bad += 1
            print('DIFFERENT', name)
    print(f'{len(cb)} base kernels, {len(cb) - bad} identical (code + descriptor + metadata); '
          f'{len(set(cn) - set(cb))} new kernels: ' + ', '.join(sorted(n[:60] for n in set(cn) - set(cb))))
    return 1 if bad else 0

if __name__ == '__main__':
    sys.exit(main())
