#!/usr/bin/env python3
"""Make static env kernel switches runtime-switchable (xtxbench GGML_HIP_RUNTIME_SWITCH_FILE hook): rewrites
`static const bool X = ggml_cuda_env_switch("GGML_HIP_...")` and getenv-lambda switches in ggml/src/ggml-cuda into
GGML_CUDA_RT_SWITCH(NAME, 1). usage: rtswitch_convert.py WORKTREE [NAME_REGEX]"""
import re, glob, sys
wt = sys.argv[1]; pat = sys.argv[2] if len(sys.argv) > 2 else r'GGML_HIP_(?:K1[0-9][0-9]|BZ)[A-Z0-9_]*'
n = 0
for p in glob.glob(f'{wt}/ggml/src/ggml-cuda/*.cu') + glob.glob(f'{wt}/ggml/src/ggml-cuda/*.cuh'):
    s = open(p).read(); o = s
    s = re.sub(r'static const bool (\w+) = ggml_cuda_env_switch\("(' + pat + r')"\);', r'const bool \1 = GGML_CUDA_RT_SWITCH("\2", 1) != 0;', s)
    s = re.sub(r'static const bool (\w+) = \[\]\(\) \{ const char \* e = getenv\("(' + pat + r')"\); return !e \|\| atoi\(e\) != 0; \}\(\);',
               r'const bool \1 = GGML_CUDA_RT_SWITCH("\2", 1) != 0;', s)
    if s != o: open(p, 'w').write(s); n += 1; print('converted', p)
print('files', n)
