#!/bin/bash
# Kernel FUSE3 graph bisect (b4) (inside run-jobs.sh): KLD vs all-off ink.kld with FUSE+FUSE2+FUSE3 and one FUSE3 cut dropped at a time
set -u
B=$HOME/wt/upstream-inkling/build-hip/bin; export LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib GGML_HIP_PM4=0 GGML_HIP_INK_FUSE=1 GGML_HIP_INK_FUSE2=1 GGML_HIP_INK_FUSE3=1
M=$HOME/models/inkling/Inkling-2-Mini-Uncensored-AD-Q4_K.gguf; T=$HOME/wt/lfm3-prof/wikitext-2-raw/wiki.test.raw; cd ~/qwen-opt/inkling
for drop in none LLAMA_INK_F3G_NOQKV LLAMA_INK_F3G_NONORM LLAMA_INK_F3G_NORELPAD LLAMA_INK_F3G_NOSINK "LLAMA_INK_F3G_NOQKV LLAMA_INK_F3G_NONORM"; do
  e=(); for v in $drop; do [ $v != none ] && e+=("$v=1"); done
  env "${e[@]}" $B/llama-perplexity -m $M -f $T -c 2048 --chunks 4 -b 2048 -ub 512 -ngl 99 -fa on --kl-divergence-base ink.kld --kl-divergence > b4.log 2>&1
  echo "drop [$drop]: $(grep -E "^Mean +KLD|^Same top p|^Mean PPL\(Q\)/PPL" b4.log | tr -s ' ' | tr '\n' ';')"
done
