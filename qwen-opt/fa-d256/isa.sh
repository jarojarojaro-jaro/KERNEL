#!/usr/bin/env bash
# CPU only, after the build: per-variant resources of flash_attn_ext_f16<256,256,32,2,false,false,false,fv> from the
# code object of the ncols1_32-ncols2_2 instance (VGPR, spills, scratch, LDS). -> res/isa.txt
set -euo pipefail
LLVM=/opt/rocm/core-10.0/lib/llvm/bin
o=$HOME/wt/fa-d256/build-hip/ggml/src/ggml-hip/CMakeFiles/ggml-hip.dir/__/ggml-cuda/template-instances/fattn-mma-f16-instance-ncols1_32-ncols2_2.cu.o
t=$(mktemp -d)
$LLVM/llvm-objcopy --dump-section .hip_fatbin="$t/fb" "$o" "$t/junk.o"
$LLVM/clang-offload-bundler --type=o --input="$t/fb" --unbundle --targets=hipv4-amdgcn-amd-amdhsa--gfx1100 --output="$t/co"
$LLVM/llvm-readelf --notes "$t/co" > "$t/notes.txt"
python3 - "$t/notes.txt" <<'EOF' | tee "$HOME/qwen-opt/fa-d256/res/isa.txt"
import re, subprocess, sys
txt = open(sys.argv[1]).read()
# each kernel's metadata block: '.name: <mangled>' + keys
for blk in re.split(r"\n\s+- \.", txt):
    m = re.search(r"\.name:\s+(\S+)", blk)
    if not m or "flash_attn_ext_f16ILi256ELi256ELi32ELi2E" not in m.group(1):
        continue
    name = m.group(1)
    dem = subprocess.run(["/opt/rocm/core-10.0/lib/llvm/bin/llvm-cxxfilt", name], capture_output=True, text=True).stdout.strip()
    g = lambda k: (re.search(r"\." + k + r":\s+(\d+)", blk) or [None, "?"])[1]
    print(f"{dem[:120]:120s} vgpr={g('vgpr_count')} vspill={g('vgpr_spill_count')} sspill={g('sgpr_spill_count')} "
          f"scratch={g('private_segment_fixed_size')} lds={g('group_segment_fixed_size')}")
EOF
rm -rf "$t"
