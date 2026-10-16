#!/usr/bin/env python3
"""Qwen3.5-0.8B GGUF -> blocks 0..14 only, output_norm = ones.

With pooling none, llama.cpp then returns rms_norm(h14) = the PFlash tap
(post_block14_residual_before_block15) divided by its RMS. The probes start with a
LayerNorm (scale invariant) and the head starts with rms_norm, so the scale is
irrelevant for all three components.
"""
import sys
import numpy as np
sys.path.insert(0, '/home/jaro/llama-master/gguf-py')
import gguf
from gguf import GGUFReader, GGUFWriter, GGUFValueType

src, dst = sys.argv[1], sys.argv[2]
keep = int(sys.argv[3]) if len(sys.argv) > 3 else 15
r = GGUFReader(src)
arch = r.fields['general.architecture'].contents()
n_layer = r.fields[f'{arch}.block_count'].contents()
w = GGUFWriter(dst, arch)
for k, f in r.fields.items():
    if k.startswith('GGUF.') or k == 'general.architecture':
        continue
    t = f.types[0]
    v = f.contents()
    if k == f'{arch}.block_count':
        v = keep
    if t == GGUFValueType.ARRAY:
        sub = f.types[-1]
        if isinstance(v, list) and len(v) == n_layer and not k.startswith('tokenizer.'):
            print('per-layer array truncated:', k, file=sys.stderr)
            v = v[:keep]
        w.add_key_value(k, v, t, sub_type=sub)
    else:
        w.add_key_value(k, v, t)
n = 0
for t in r.tensors:
    name = t.name
    if name.startswith('blk.') and int(name.split('.')[1]) >= keep:
        continue
    if name == 'output_norm.weight':
        w.add_tensor(name, np.ones(t.data.shape, dtype=np.float32))
    elif t.tensor_type == gguf.GGMLQuantizationType.F32:
        w.add_tensor(name, np.asarray(t.data))
    else:
        w.add_tensor(name, np.asarray(t.data), raw_dtype=t.tensor_type)
    n += 1
w.write_header_to_file()
w.write_kv_data_to_file()
w.write_tensors_to_file()
w.close()
print('kept tensors', n, 'of', len(r.tensors))
