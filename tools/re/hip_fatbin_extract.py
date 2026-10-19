#!/usr/bin/env python3
"""Extract AMDGPU code objects from the .hip_fatbin section of a HIP host .so.

Parses uncompressed __CLANG_OFFLOAD_BUNDLE__ records (one per translation unit)
and writes each hipv4-amdgcn-* entry as <outdir>/<idx>.<target>.co.
Pure Python, CPU only. Compressed (CCOB) bundles are reported, not decoded:
use clang-offload-bundler for those.

usage: hip_fatbin_extract.py <lib.so> <outdir> [--filter SUBSTR]
  --filter keeps only code objects whose bytes contain SUBSTR (e.g. a kernel
  name fragment such as mul_mat_vec_q).
"""
import mmap
import os
import struct
import sys

MAGIC = b"__CLANG_OFFLOAD_BUNDLE__"


def bundles(m):
    i = m.find(MAGIC)
    while i != -1:
        yield i
        i = m.find(MAGIC, i + len(MAGIC))


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    lib, out = sys.argv[1], sys.argv[2]
    filt = None
    if "--filter" in sys.argv:
        filt = sys.argv[sys.argv.index("--filter") + 1].encode()
    os.makedirs(out, exist_ok=True)
    with open(lib, "rb") as f:
        m = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        if m.find(b"CCOB") != -1:
            print("warning: compressed CCOB bundles present; not decoded", file=sys.stderr)
        n_written = 0
        for bi, base in enumerate(bundles(m)):
            p = base + len(MAGIC)
            (n,) = struct.unpack_from("<Q", m, p)
            p += 8
            for _ in range(n):
                off, size, idlen = struct.unpack_from("<QQQ", m, p)
                p += 24
                tid = m[p : p + idlen].decode()
                p += idlen
                if not tid.startswith("hip") or size == 0:
                    continue
                blob = m[base + off : base + off + size]
                if filt and filt not in blob:
                    continue
                target = tid.split("-")[-1].replace(":", "_")
                path = os.path.join(out, f"{bi:03d}.{target}.co")
                with open(path, "wb") as g:
                    g.write(blob)
                n_written += 1
                print(f"{path}\t{size}\t{tid}")
        print(f"bundles={bi + 1} written={n_written}", file=sys.stderr)


if __name__ == "__main__":
    main()
