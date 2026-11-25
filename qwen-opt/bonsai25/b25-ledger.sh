#!/usr/bin/env bash
# Bonsai 2.5 round ledger on XTX: ms for a batch of m tokens at depth d (= verify(m) cost; m=1 = plain token), topka-rt (topka-k157 + runtime switches), production env.
set -uo pipefail
source ~/qwen-opt/perf-tools/profiles/bonsai25.env
B=~/wt/topka-rt/build-hip/bin
~/qwen-opt/l1tok/chat8080.sh stop
for d in 1024 8192; do
  env $RUN_ENV GGML_HIP_K157_MMVF_THIN=0 LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib taskset -c 2-5 timeout 400 $B/llama-bench -m $MODEL -ngl 999 -fa 1 -ctk q4_0 -ctv q4_0 \
    -p 1,2,3,4,5,8,16 -n 0 -d $d -ub 512 -r 5 -o md 2>&1 | grep -E "^\|" | sed "s/^/LEDGER d=$d /"
done
echo "gfxhub $(journalctl -k --since '-15min' --no-pager | grep -c gfxhub)"
