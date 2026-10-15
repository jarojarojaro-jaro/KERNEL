#!/usr/bin/env python3
"""Weight-damage canary: copy a GGUF and scale the dequantized values of selected tensors by (1+delta).

  perturb_gguf.py SRC DST --tensor REGEX --delta 0.02 [--verify] [--dry-run] [--min-free-gb 10]

Only the fp16 block scales are rewritten (in place in the copy, everything else is byte-identical):
  Q8_0  34 B block:  d @0                      x = d*q
  Q4_K 144 B block:  d @0, dmin @2             x = d*sc*q - dmin*m      (both scaled -> x scales)
  Q5_K 176 B block:  d @0, dmin @2             x = d*sc*q - dmin*m
  Q6_K 210 B block:  d @208 (end of block)     x = d*sc*q
The new scale is fp16(fp32(d)*(1+delta)), so the realised factor per block is exact to fp16 rounding (<= 2^-11).
REGEX is matched with re.fullmatch against tensor names (e.g. 'blk\\.10\\.ffn_down_exps\\.weight').
--verify re-reads both files: bytes outside the scale fields identical (whole file), dequantized values of the
selected tensors = (1+delta) x original (least-squares factor within 1e-3, max error <= 4e-3 x max|x|).
The copy is written to DST.part and renamed when complete. CPU only; needs gguf-py (PYTHONPATH) and numpy.
"""
import argparse
import os
import re
import shutil
import sys

import numpy as np
from gguf import GGUFReader, GGMLQuantizationType as QT
from gguf.constants import GGML_QUANT_SIZES
from gguf.quants import dequantize

# type -> (block bytes, byte offsets of the fp16 scales that multiply every value of the block)
SCALE_FIELDS = {
    QT.Q8_0: (34, (0,)),
    QT.Q4_K: (144, (0, 2)),
    QT.Q5_K: (176, (0, 2)),
    QT.Q6_K: (210, (208,)),
}
for _t, (_bs, _) in SCALE_FIELDS.items():
    assert GGML_QUANT_SIZES[_t][1] == _bs, (_t, GGML_QUANT_SIZES[_t])

CHUNK = 64 << 20  # bytes per compare slice
DQ_CHUNK = 8 << 20  # quantized bytes per dequantize slice (~8x that in float64)


def select(reader, pattern):
    rx = re.compile(pattern)
    sel = [t for t in reader.tensors if rx.fullmatch(t.name)]
    if not sel:
        raise SystemExit(f'no tensor matches {pattern!r}')
    bad = [f'{t.name} ({t.tensor_type.name})' for t in sel if t.tensor_type not in SCALE_FIELDS]
    if bad:
        raise SystemExit('unsupported tensor type(s): ' + ', '.join(bad) +
                         ' (supported: ' + ', '.join(t.name for t in SCALE_FIELDS) + ')')
    return sel


def scale_fields(blocks, fields, factor):
    """Scale the fp16 fields (byte offsets) of a (n_blocks, block_bytes) uint8 view in place."""
    for off in fields:
        h = np.ascontiguousarray(blocks[:, off:off + 2]).view('<f2').reshape(-1)
        new = (h.astype(np.float32) * np.float32(factor)).astype('<f2')
        if not np.isfinite(new).all():
            raise SystemExit('fp16 overflow while scaling (delta too large)')
        blocks[:, off:off + 2] = new.view(np.uint8).reshape(-1, 2)


def scale_mask(bs, fields):
    m = np.zeros(bs, dtype=bool)
    for off in fields:
        m[off:off + 2] = True
    return m


def compare_outside(src, dst, ranges):
    """Byte-compare the two files outside the given sorted (start, end) ranges."""
    size = os.path.getsize(src)
    if os.path.getsize(dst) != size:
        raise SystemExit(f'verify: size differs {size} vs {os.path.getsize(dst)}')
    a = np.memmap(src, dtype=np.uint8, mode='r')
    b = np.memmap(dst, dtype=np.uint8, mode='r')
    pos = 0
    for start, end in ranges + [(size, size)]:
        for s in range(pos, start, CHUNK):
            e = min(s + CHUNK, start)
            if not np.array_equal(a[s:e], b[s:e]):
                raise SystemExit(f'verify: unexpected byte change in [{s}, {e})')
        pos = end


def verify(src, dst, sel, factor):
    rd = GGUFReader(dst)
    dt = {t.name: t for t in rd.tensors}
    ranges = []
    for t in sel:
        u = dt[t.name]
        if (u.data_offset, u.n_bytes, u.tensor_type) != (t.data_offset, t.n_bytes, t.tensor_type):
            raise SystemExit(f'verify: layout of {t.name} differs')
        bs, fields = SCALE_FIELDS[t.tensor_type]
        keep = ~scale_mask(bs, fields)
        a = t.data.reshape(-1).view(np.uint8).reshape(-1, bs)
        b = u.data.reshape(-1).view(np.uint8).reshape(-1, bs)
        step = max(1, DQ_CHUNK // bs)
        num = den = err = amax = 0.0
        n_changed = 0
        for s in range(0, a.shape[0], step):
            xa, xb = a[s:s + step], b[s:s + step]
            if not np.array_equal(xa[:, keep], xb[:, keep]):
                raise SystemExit(f'verify: {t.name}: bytes other than the scales changed')
            n_changed += int((xa[:, ~keep] != xb[:, ~keep]).any(axis=1).sum())
            va = dequantize(xa, t.tensor_type).astype(np.float64).reshape(-1)
            vb = dequantize(xb, t.tensor_type).astype(np.float64).reshape(-1)
            num += float(va @ vb)
            den += float(va @ va)
            err = max(err, float(np.abs(vb - factor * va).max()))
            amax = max(amax, float(np.abs(va).max()))
        ls = num / den if den else float('nan')
        rel = err / amax if amax else 0.0
        print(f'verify {t.name}: blocks {a.shape[0]}, scale changed in {n_changed}, '
              f'least-squares factor {ls:.6f} (want {factor:.6f}), max |x1-f*x0|/max|x0| {rel:.2e}')
        if not (abs(ls - factor) <= 1e-3 * factor and rel <= 4e-3):
            raise SystemExit(f'verify: {t.name}: dequantized values not scaled by {factor}')
        ranges.append((t.data_offset, t.data_offset + t.n_bytes))
    compare_outside(src, dst, sorted(ranges))
    print('verify: all other bytes identical')


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('src')
    p.add_argument('dst')
    p.add_argument('--tensor', required=True, help='regex (fullmatch) of tensor names')
    p.add_argument('--delta', type=float, required=True, help='relative scale change, e.g. 0.02')
    p.add_argument('--verify', action='store_true')
    p.add_argument('--dry-run', action='store_true', help='list the selected tensors, write nothing')
    p.add_argument('--min-free-gb', type=float, default=10.0, help='free space to leave after the copy')
    a = p.parse_args()
    factor = 1.0 + a.delta
    if os.path.abspath(a.src) == os.path.abspath(a.dst):
        raise SystemExit('dst must differ from src')
    if os.path.exists(a.dst):
        raise SystemExit(f'{a.dst} exists')
    reader = GGUFReader(a.src)
    sel = select(reader, a.tensor)
    for t in sel:
        print(f'{t.name} {t.tensor_type.name} {list(map(int, t.shape))} {t.n_bytes} B @ {t.data_offset}: '
              f'scales x{factor:g}')
    if a.dry_run:
        return 0
    size = os.path.getsize(a.src)
    ddir = os.path.dirname(os.path.abspath(a.dst))
    free = shutil.disk_usage(ddir).free
    if free < size + a.min_free_gb * 2**30:
        raise SystemExit(f'not enough space in {ddir}: {free / 2**30:.1f} GiB free, need '
                         f'{size / 2**30:.1f} + {a.min_free_gb:g} GiB')
    part = a.dst + '.part'
    shutil.copyfile(a.src, part)
    mm = np.memmap(part, dtype=np.uint8, mode='r+')
    for t in sel:
        bs, fields = SCALE_FIELDS[t.tensor_type]
        scale_fields(mm[t.data_offset:t.data_offset + t.n_bytes].reshape(-1, bs), fields, factor)
    mm.flush()
    del mm
    with open(part, 'rb') as f:
        os.fsync(f.fileno())
    if a.verify:
        verify(a.src, part, sel, factor)
    os.rename(part, a.dst)
    print(f'wrote {a.dst}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
