#!/bin/bash
# Gemini ink-r5 gate (inside run-jobs.sh): INK_FUSE3 (convolve, rel-bias+sink+mask, situ matcher, wqgrkv packing) on top of
# FUSE+FUSE2 (+ r5 mutual-exclusion fix). md5 / kld (vs all-off ink.kld from r3) / abab tg64 (PM4+NOBLAS on, FUSE3 0/1 and
# PM4 off) / dbg tape stats
set -u
B=$HOME/wt/upstream-inkling/build-hip/bin; export LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib GGML_HIP_INK_FUSE=1 GGML_HIP_INK_FUSE2=1 GGML_HIP_INK_NOBLAS=1
M=$HOME/models/inkling/Inkling-2-Mini-Uncensored-AD-Q4_K.gguf; T=$HOME/wt/lfm3-prof/wikitext-2-raw/wiki.test.raw; cd ~/qwen-opt/inkling
P0="GGML_HIP_PM4=0"; P1="GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0"
PR="Explain in three sentences why the sky is blue, then list five prime numbers."
case ${1:-} in
  md5) for c in "$P0 GGML_HIP_INK_FUSE3=0" "$P0 GGML_HIP_INK_FUSE3=1" "$P1 GGML_HIP_INK_FUSE3=1"; do
         out=$(env $c $B/llama-completion -m $M -p "$PR" -n 128 --temp 0 --seed 42 -fa on -ngl 99 -no-cnv --no-display-prompt 2>/dev/null)
         echo "${c% GGML*} ${c##* } md5=$(printf '%s' "$out" | md5sum | cut -c1-8) | ${out:0:120}" | tr '\n' ' '; echo; done ;;
  kld) P=(-f $T -c 2048 --chunks 4 -b 2048 -ub 512 -ngl 99 -fa on --kl-divergence-base ink.kld --kl-divergence)
       for f3 in 0 1; do env $P0 GGML_HIP_INK_FUSE3=$f3 $B/llama-perplexity -m $M "${P[@]}" > kld-r5-$f3.log 2>&1
         echo "FUSE+FUSE2+NOBLAS FUSE3=$f3: $(grep -E "^Mean +KLD|^Same top p|^Mean PPL\(Q\)/PPL|^Maximum KLD" kld-r5-$f3.log | tr -s ' ' | tr '\n' ';')"; done ;;
  abab) for c in "$P1 GGML_HIP_INK_FUSE3=0" "$P1 GGML_HIP_INK_FUSE3=1" "$P0 GGML_HIP_INK_FUSE3=1" "$P0 GGML_HIP_INK_FUSE3=1" "$P1 GGML_HIP_INK_FUSE3=1" "$P1 GGML_HIP_INK_FUSE3=0"; do
          r=$(env $c $B/llama-bench -m $M -p 0 -n 64 -fa 1 -ngl 99 -r 5 2>&1 | grep tg64 | awk -F'|' '{print $(NF-1)}')
          echo "${c%% *} ${c##* } tg64 $r"; done ;;
  dbg) env $P1 GGML_HIP_INK_FUSE3=1 GGML_HIP_PM4_DEBUG=2 $B/llama-completion -m $M -p "$PR" -n 32 --temp 0 -fa on -ngl 99 -no-cnv 2>&1 | grep -E "pm4" | grep -v guard | cut -c1-160 | sort | uniq -c | sort -rn | head -8 ;;
esac
