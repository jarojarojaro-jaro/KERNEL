#!/usr/bin/env bash
# PPL of the lossless repack: PTQ1_0 vs Q2_0 (same codes, different kernels), 40 chunks x 512 of xtxbench corpus, prism build
set -uo pipefail
B=$HOME/wt/prism/build-hip/bin; export GGML_HIP_PM4=0 LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib; D=$HOME/models/bonsai25
~/qwen-opt/l1tok/chat8080.sh stop
for m in PTQ1_0 Q2_0; do
  echo "== $m"; taskset -c 2-5 timeout 280 $B/llama-perplexity -m $D/Ternary-Bonsai-2.5-27B-Uncensored-$m-mtp.gguf -ngl 999 -fa on \
     -f ~/qwen-opt/xtxbench/corpus.txt -c 512 --chunks 40 2>&1 | grep -E "Final estimate|\[40\]"
done
journalctl -k --since "-10min" --no-pager | grep -c gfxhub
