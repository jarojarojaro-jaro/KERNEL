#!/usr/bin/env bash
# One kernel experiment: write tuning macros, rebuild ggml-hip, run the cache-cold microbench.
# usage: exp.sh LABEL "MACRO=VAL MACRO2=VAL" [ncols] [type-filter]
set -euo pipefail
label=$1; macros=$2; ncols=${3:-1,2,4,8}; filt=${4:-}
L=~/llama-master
inc=$L/ggml/src/ggml-cuda/mmvq-tune.inc
: > "$inc"
for m in $macros; do echo "#define ${m%%=*} ${m#*=}" >> "$inc"; done
export PATH=/opt/rocm/core-10.0/bin:$PATH
cmake --build $L/build-hip --target ggml-hip -j16 2>&1 | grep -E 'error|warning: .*spill' | head -20 || true
cd ~/qwen-opt/mmvq-bench
mkdir -p runs
LD_LIBRARY_PATH=/opt/rocm/core-10.0/lib ./mmvq_bench "$ncols" "$filt" 2>/dev/null | grep -v '^#' > "runs/$label.txt"
cat "runs/$label.txt"
