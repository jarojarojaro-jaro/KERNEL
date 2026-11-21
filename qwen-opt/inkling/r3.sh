#!/bin/bash
# Gemini ink-r3 gate (inside run-jobs.sh): INK_FUSE (r1) + INK_FUSE2 (r3, vLLM loop fusions) on AtomicChat AD-Q4_K, PM4=0
# (PM4 tape falls back on this graph: rocBLAS Cijk kernel without metadata). md5 / kld (wikitext 2x2048, base = all off) /
# abab tg64 / xl = unsloth UD-Q4_K_XL load (r3 loader fix) + tg64
set -u
B=$HOME/wt/upstream-inkling/build-hip/bin; export LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib GGML_HIP_PM4=0
M=$HOME/models/inkling/Inkling-2-Mini-Uncensored-AD-Q4_K.gguf; X=$HOME/models/inkling/Inkling-2-Mini-UD-Q4_K_XL.gguf
T=$HOME/wt/lfm3-prof/wikitext-2-raw/wiki.test.raw; cd ~/qwen-opt/inkling
PR="Explain in three sentences why the sky is blue, then list five prime numbers."
f() { echo "GGML_HIP_INK_FUSE=$1 GGML_HIP_INK_FUSE2=$2"; }
case ${1:-} in
  md5) for c in "0 0" "1 0" "0 1" "1 1"; do set -- $c
         out=$(env $(f $1 $2) $B/llama-completion -m $M -p "$PR" -n 128 --temp 0 --seed 42 -fa on -ngl 99 -no-cnv --no-display-prompt 2>/dev/null)
         echo "FUSE=$1 FUSE2=$2 md5=$(printf '%s' "$out" | md5sum | cut -c1-8) | ${out:0:160}" | tr '\n' ' '; echo; done ;;
  kld) P=(-f $T -c 2048 --chunks 4 -b 2048 -ub 512 -ngl 99 -fa on)
       env $(f 0 0) $B/llama-perplexity -m $M "${P[@]}" --kl-divergence-base ink.kld > kld-base.log 2>&1; grep -E "Final estimate" kld-base.log
       for c in "1 0" "0 1" "1 1"; do set -- $c
         env $(f $1 $2) $B/llama-perplexity -m $M "${P[@]}" --kl-divergence-base ink.kld --kl-divergence > kld-$1$2.log 2>&1
         echo "FUSE=$1 FUSE2=$2: $(grep -E "^Mean +KLD|^Same top p|^Mean PPL\(Q\)|^Maximum KLD" kld-$1$2.log | tr -s ' ' | tr '\n' ';')"; done ;;
  abab) for c in "0 0" "1 0" "0 1" "1 1" "1 1" "0 1" "1 0" "0 0"; do set -- $c
          r=$(env $(f $1 $2) $B/llama-bench -m $M -p 0 -n 64 -fa 1 -ngl 99 -r 3 2>&1 | grep tg64 | awk -F'|' '{print $(NF-1)}')
          echo "FUSE=$1 FUSE2=$2 tg64 $r"; done ;;
  xl) for c in "0 0" "1 1"; do set -- $c; echo "XL FUSE=$1 FUSE2=$2: $(env $(f $1 $2) $B/llama-bench -m $X -p 512 -n 64 -fa 1 -ngl 99 -r 2 2>&1 | grep -E "pp512|tg64|error" | awk -F'|' '{print $(NF-2), $(NF-1)}' | tr '\n' ' ')"; done ;;
esac
