#!/usr/bin/env bash
# KLD of a build vs the base Hadamard port (topka-bonsai c76335b): 40 x 512 tokens of xtxbench corpus, Q2_0 Bonsai 2.5 Uncensored
set -uo pipefail
M=$HOME/models/bonsai25/Ternary-Bonsai-2.5-27B-Uncensored-Q2_0-mtp.gguf; C=$HOME/qwen-opt/xtxbench/corpus.txt; L=/tmp/b25-base.kld
export GGML_HIP_PM4=0
~/qwen-opt/l1tok/chat8080.sh stop
B=$HOME/wt/topka-bonsai/build-hip/bin
[ -s $L ] || LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib taskset -c 2-5 timeout 400 $B/llama-perplexity -m $M -ngl 999 -fa on -f $C -c 512 --chunks 40 --kl-divergence-base $L 2>&1 | grep -E "Final estimate"
for spec in "$@"; do B=${spec%%@*}; E=""; [[ $spec == *@* ]] && E=${spec#*@}
  echo "== $B ${E:-default}"
  env ${E//,/ } LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib taskset -c 2-5 timeout 400 $B/llama-perplexity -m $M -ngl 999 -fa on -f $C -c 512 --chunks 40 \
    --kl-divergence-base $L --kl-divergence 2>&1 | grep -E "Mean PPL|Mean    KLD|Maximum KLD|99.9%  KLD|Same top p|Mean KLD"
done
echo "gfxhub $(journalctl -k --since "-15min" --no-pager | grep -c gfxhub)"
