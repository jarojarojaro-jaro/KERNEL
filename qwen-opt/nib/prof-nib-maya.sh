#!/usr/bin/env bash
# K-162: plain decode kernel ledger, Nib vs Maya production engine, same card, rocprofv3 kernel stats -> us/token per kernel
set -uo pipefail
O=$HOME/qwen-opt/nib/prof-$(date +%H%M); mkdir -p $O; export GGML_HIP_PM4=0
~/qwen-opt/l1tok/chat8080.sh stop
P=/opt/rocm/core-10.0/bin/rocprofv3
# Nib: bench, plain decode 128 tokens at depth 0, dense attention, KV q4_0
mkdir -p $O/nib && cd $O/nib && taskset -c 2-5 timeout 300 $P --kernel-trace --stats --output-format csv -d . -o p -- \
  $HOME/wt/nib/build/nib bench -m $HOME/models/nib/Inkling-2-Mini-NVFP4-Mixed.gguf -c 32768 -d 0 -p 512 -n 128 -r 1 --kv-type q4_0 --sparse-pages 0 > bench.txt 2>&1
grep -E "^\|" bench.txt | tail -3
# Maya production binary + env (maya-atomic.json), CLI generation of 128 tokens from a 64-token prompt, no drafting
T=$(python3 -c "print(','.join(str(1000+i) for i in range(64)))")
mkdir -p $O/maya && cd $O/maya && env LD_LIBRARY_PATH=/opt/rocm/core-10.0/lib IK2_KV=q4 IK2_HIP_COMB=1 IK2_HIP_EXPV=1 IK2_HIP_FUSE=1 IK2_HIP_LGD=2 IK2_HIP_LGR=1 IK2_HIP_MVF16=1 IK2_HIP_NT=15 IK2_HIP_PCONV=1 \
  taskset -c 2-5 timeout 300 $P --kernel-trace --stats --output-format csv -d . -o p -- \
  $HOME/k134/maya/build-hip/maya-ik2.adq4k-dpp-sfx --model $HOME/models/inkling/Inkling-2-Mini-Uncensored-AD-Q4_K.gguf --tokens $T --gen 129 --ctx 32768 > gen.txt 2>&1
grep -iE "tok/s|decode|ms" gen.txt | tail -4
for e in nib maya; do f=$(find $O/$e -name "*kernel_stats.csv" | head -1); echo "== $e ledger (us per decoded token, all kernels incl. prefill/load)"; python3 ~/qwen-opt/perf-tools/ledger.py $f 128 --top 22; done
echo "gfxhub $(journalctl -k --since '-15min' --no-pager | grep -c gfxhub)"
