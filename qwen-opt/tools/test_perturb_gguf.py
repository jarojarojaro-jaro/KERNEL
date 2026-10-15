#!/usr/bin/env python3
"""CPU self-test of perturb_gguf.py on a small fake GGUF (GGUFWriter): Q8_0, Q4_K, Q5_K, Q6_K and F32 tensors.

  PYTHONPATH=~/llama-master/gguf-py ~/qwen-opt/.venv-kt/bin/python test_perturb_gguf.py

Checks, independently of perturb_gguf.py --verify: every changed byte lies in a scale field (Q8_0 d @0, Q4_K/Q5_K
d @0 + dmin @2, Q6_K d @208) of a selected tensor, every selected block's scales are fp16(old*(1+delta)), the
dequantized values scale by (1+delta), unselected tensors and the header are untouched, unsupported types are refused.
"""
import os
import subprocess
import sys
import tempfile

import numpy as np
from gguf import GGUFReader, GGUFWriter, GGMLQuantizationType as QT
from gguf.quants import dequantize, quantize

HERE = os.path.dirname(os.path.abspath(__file__))
FIELDS = {QT.Q8_0: (34, 32, (0,)), QT.Q4_K: (144, 256, (0, 2)), QT.Q5_K: (176, 256, (0, 2)), QT.Q6_K: (210, 256, (208,))}
rng = np.random.default_rng(1234)


def fake_kquant(qt, rows, cols):
    bs, n, fields = FIELDS[qt]
    blocks = rng.integers(0, 256, size=(rows * cols // n, bs), dtype=np.uint8)
    for off in fields:  # random bytes could be inf/NaN scales: write sane positive fp16 scales
        d = rng.uniform(1e-3, 2e-2, size=blocks.shape[0]).astype('<f2')
        blocks[:, off:off + 2] = d.view(np.uint8).reshape(-1, 2)
    return blocks.reshape(rows, cols // n * bs)


def build(path):
    w = GGUFWriter(path, 'llama')
    w.add_block_count(3)
    tensors = {
        'blk.0.ffn_down.weight': (QT.Q6_K, fake_kquant(QT.Q6_K, 8, 512)),
        'blk.0.attn_output.weight': (QT.Q5_K, fake_kquant(QT.Q5_K, 8, 512)),
        'blk.1.ffn_down.weight': (QT.Q4_K, fake_kquant(QT.Q4_K, 8, 512)),
        'blk.1.attn_output.weight': (QT.Q8_0, quantize(rng.standard_normal((8, 512)).astype(np.float32), QT.Q8_0)),
        'blk.1.ffn_norm.weight': (QT.F32, rng.standard_normal(512).astype(np.float32)),
        'blk.2.ffn_down.weight': (QT.Q6_K, fake_kquant(QT.Q6_K, 8, 512)),
        'blk.2.attn_output.weight': (QT.Q5_K, fake_kquant(QT.Q5_K, 8, 512)),
    }
    for name, (qt, data) in tensors.items():
        w.add_tensor(name, data, raw_dtype=qt if qt != QT.F32 else None)
    w.write_header_to_file()
    w.write_kv_data_to_file()
    w.write_tensors_to_file()
    w.close()


def run(*args):
    return subprocess.run([sys.executable, os.path.join(HERE, 'perturb_gguf.py'), *args],
                          capture_output=True, text=True)


def check(src, dst, regex_names, delta):
    a = np.fromfile(src, dtype=np.uint8)
    b = np.fromfile(dst, dtype=np.uint8)
    assert a.size == b.size, 'size changed'
    changed = np.flatnonzero(a != b)
    allowed = np.zeros(a.size, dtype=bool)
    ra, rb = GGUFReader(src), {t.name: t for t in GGUFReader(dst).tensors}
    factor = 1.0 + delta
    for t in ra.tensors:
        if t.name not in regex_names:
            continue
        bs, _, fields = FIELDS[t.tensor_type]
        nb = t.n_bytes // bs
        for off in fields:
            pos = t.data_offset + off + bs * np.arange(nb)
            allowed[pos] = allowed[pos + 1] = True
            old = a[pos[:, None] + np.arange(2)].copy().view('<f2').reshape(-1)
            new = b[pos[:, None] + np.arange(2)].copy().view('<f2').reshape(-1)
            want = (old.astype(np.float32) * np.float32(factor)).astype('<f2')
            assert np.array_equal(new, want), f'{t.name}: scale @{off} not fp16(old*{factor})'
        x0 = dequantize(t.data, t.tensor_type).astype(np.float64)
        x1 = dequantize(rb[t.name].data, t.tensor_type).astype(np.float64)
        ls = float((x0 * x1).sum() / (x0 * x0).sum())
        rel = float(np.abs(x1 - factor * x0).max() / np.abs(x0).max())
        assert abs(ls - factor) < 1e-3 * factor and rel < 4e-3, (t.name, ls, rel)
        print(f'  {t.name:26s} {t.tensor_type.name:5s} blocks {nb:3d}  ls factor {ls:.6f} (want {factor:.6f})  '
              f'max err/max|x| {rel:.1e}')
    assert allowed[changed].all(), f'{(~allowed[changed]).sum()} changed bytes outside scale fields'
    print(f'  changed bytes {changed.size}, all inside scale fields of {sorted(regex_names)}')


def main():
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, 'fake.gguf')
        build(src)
        sel = {'blk.0.ffn_down.weight', 'blk.0.attn_output.weight', 'blk.1.ffn_down.weight', 'blk.1.attn_output.weight'}
        for i, delta in enumerate((0.005, 0.02, 0.10, -0.05)):
            dst = os.path.join(tmp, f'p{i}.gguf')
            r = run(src, dst, '--tensor', r'blk\.[01]\.(ffn_down|attn_output)\.weight', '--delta', str(delta),
                    '--verify', '--min-free-gb', '0')
            assert r.returncode == 0, r.stdout + r.stderr
            print(f'delta {delta}: perturb_gguf.py --verify ok')
            check(src, dst, sel, delta)
        r = run(src, os.path.join(tmp, 'x.gguf'), '--tensor', r'blk\.1\.ffn_norm\.weight', '--delta', '0.1')
        assert r.returncode != 0 and 'unsupported' in r.stderr, r.stderr
        r = run(src, os.path.join(tmp, 'x.gguf'), '--tensor', r'nope', '--delta', '0.1')
        assert r.returncode != 0 and 'no tensor matches' in r.stderr, r.stderr
        r = run(src, os.path.join(tmp, 'p0.gguf'), '--tensor', r'blk\.0\.ffn_down\.weight', '--delta', '0.1')
        assert r.returncode != 0 and 'exists' in r.stderr, r.stderr
        assert not os.path.exists(os.path.join(tmp, 'x.gguf'))
        print('refusals ok (F32 tensor, no match, existing dst)')
    print('ALL OK')


if __name__ == '__main__':
    main()
