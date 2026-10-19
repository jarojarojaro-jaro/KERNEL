#!/usr/bin/env python3
"""co_stats.py OUT.csv INPUT... [--arch gfx1100]

Per-kernel resources of AMDGPU code objects, CPU only (ROCm LLVM tools, no GPU):
  INPUT = host .so with .hip_fatbin (all __CLANG_OFFLOAD_BUNDLE__ bundles are split),
          offload bundle (.co / .hsaco from hipBLASLt / rocBLAS), or a plain AMDGPU ELF.
Columns: vgpr, sgpr, spills, scratch, LDS, wave size and VGPR-limited waves/SIMD on gfx1100
(min(16, 1536 // roundup(vgpr, 24)); matches the compiler's "; Occupancy" and RGA "allocation granularity: 24").
"""
import concurrent.futures as cf
import csv
import os
import re
import struct
import subprocess
import sys
import tempfile

import yaml

LLVM = '/opt/rocm/llvm/bin/'
MAGIC = b'__CLANG_OFFLOAD_BUNDLE__'
Loader = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)


def split_bundles(data, arch):
    """Yield the code objects for `arch` from every offload bundle in `data`."""
    pos = data.find(MAGIC)
    while pos >= 0:
        n, = struct.unpack_from('<Q', data, pos + 24)
        q = pos + 32
        for _ in range(n):
            off, size, il = struct.unpack_from('<QQQ', data, q)
            q += 24
            tid = data[q:q + il].decode()
            q += il
            if tid.endswith(arch) and size:
                yield data[pos + off:pos + off + size]
        pos = data.find(MAGIC, pos + 1)


def unbundle_compressed(blob, arch, tmp, stem):
    """Compressed offload bundle (CCOB, clang --offload-compress): let clang-offload-bundler decompress it."""
    src, dst = os.path.join(tmp, stem + '.ccob'), os.path.join(tmp, stem + '.hsaco')
    open(src, 'wb').write(blob)
    r = subprocess.run([LLVM + 'clang-offload-bundler', '--unbundle', '--type=o', '--input=' + src,
                        '--targets=hipv4-amdgcn-amd-amdhsa--' + arch, '--output=' + dst], capture_output=True)
    return [dst] if r.returncode == 0 and os.path.getsize(dst) else []


def code_objects(path, arch, tmp):
    data = open(path, 'rb').read()
    stem = os.path.basename(path)
    if data[:4] == b'CCOB':
        return unbundle_compressed(data, arch, tmp, stem)
    if data[:4] == b'\x7fELF' and MAGIC not in data[:1 << 20] and b'.hip_fatbin' not in data:
        return [path]  # plain AMDGPU ELF
    if data[:4] == b'\x7fELF' and b'.hip_fatbin' in data:
        sec = os.path.join(tmp, 'fatbin.bin')
        subprocess.run([LLVM + 'llvm-objcopy', '--dump-section=.hip_fatbin=' + sec, path, os.devnull], check=True)
        data = open(sec, 'rb').read()
    out = []
    for i, co in enumerate(split_bundles(data, arch)):
        fn = os.path.join(tmp, f'{stem}.{i}.hsaco')
        open(fn, 'wb').write(co)
        out.append(fn)
    # compressed bundles inside a fatbin: each CCOB chunk runs to the next bundle marker (the header carries its size)
    marks = [m.start() for m in re.finditer(b'CCOB|' + MAGIC, data)] if b'CCOB' in data else []
    for j, p in enumerate(marks):
        if data.startswith(b'CCOB', p):
            end = marks[j + 1] if j + 1 < len(marks) else len(data)
            out += unbundle_compressed(data[p:end], arch, tmp, f'{stem}.c{j}')
    return out


def kernels(hsaco):
    notes = subprocess.run([LLVM + 'llvm-readelf', '--notes', hsaco], capture_output=True, text=True).stdout
    i = notes.find('amdhsa.kernels')
    if i < 0:
        return []
    doc = notes[notes.rfind('---', 0, i):]
    return yaml.load(doc[:doc.find('\n...')], Loader=Loader)['amdhsa.kernels']


def waves(vgpr):
    return min(16, 1536 // (-(-max(vgpr, 1) // 24) * 24))


def main():
    args = sys.argv[1:]
    arch = 'gfx1100'
    if '--arch' in args:
        i = args.index('--arch')
        arch = args[i + 1]
        del args[i:i + 2]
    out, inputs = args[0], args[1:]
    with tempfile.TemporaryDirectory() as tmp:
        cos = [(p, co) for p in inputs for co in code_objects(p, arch, tmp)]
        with cf.ThreadPoolExecutor(4) as ex:
            ks = [(p, k) for (p, _), lst in zip(cos, ex.map(kernels, [c for _, c in cos])) for k in lst]
    names = subprocess.run([LLVM + 'llvm-cxxfilt'], input='\n'.join(k['.name'] for _, k in ks),
                           capture_output=True, text=True).stdout.splitlines()
    g = lambda k, key: k.get(key) or 0
    with open(out, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['source', 'kernel_demangled', 'vgpr', 'sgpr', 'vgpr_spill', 'sgpr_spill', 'scratch_B', 'lds_B',
                    'wave', 'waves_per_simd_vgpr_limited'])
        for (p, k), dn in zip(ks, names):
            v = g(k, '.vgpr_count')
            w.writerow([os.path.basename(p), dn, v, g(k, '.sgpr_count'), g(k, '.vgpr_spill_count'),
                        g(k, '.sgpr_spill_count'), g(k, '.private_segment_fixed_size'),
                        g(k, '.group_segment_fixed_size'), g(k, '.wavefront_size'), waves(v)])
    print(f'{len(ks)} kernels from {len(cos)} code objects -> {out}')


if __name__ == '__main__':
    main()
