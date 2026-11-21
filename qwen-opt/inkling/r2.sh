#!/bin/bash
# Gemini ink-r2 gate on the XTX (inside run-jobs.sh): PM4 tape port + INK_FUSE on Inkling 2 Mini (AtomicChat AD-Q4_K).
# md5 = greedy 128 tokens in 4 configs (PM4 must be bit-identical); dbg = PM4_DEBUG=2 tape build stats; abab = tg64 2x2 ABBA
set -u
B=$HOME/wt/upstream-inkling/build-hip/bin; export LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib
M=$HOME/models/inkling/Inkling-2-Mini-Uncensored-AD-Q4_K.gguf
P0="GGML_HIP_PM4=0"; P1="GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0"
PR="Explain in three sentences why the sky is blue, then list five prime numbers."
cfg() { [ $1 = 1 ] && echo "$P1 GGML_HIP_INK_FUSE=$2" || echo "$P0 GGML_HIP_INK_FUSE=$2"; }
case ${1:-} in
  md5) for c in "0 0" "0 1" "1 0" "1 1"; do set -- $c
         out=$(env $(cfg $1 $2) $B/llama-completion -m $M -p "$PR" -n 128 --temp 0 --seed 42 -fa on -ngl 99 -no-cnv --no-display-prompt 2>/dev/null)
         echo "PM4=$1 FUSE=$2 md5=$(printf '%s' "$out" | md5sum | cut -c1-8) len=${#out}"; done
       echo "--- text PM4=0 FUSE=0:"; env $(cfg 0 0) $B/llama-completion -m $M -p "$PR" -n 64 --temp 0 -fa on -ngl 99 -no-cnv --no-display-prompt 2>/dev/null | head -c 400 ;;
  dbg) for f in 0 1; do echo "== FUSE=$f"; env $(cfg 1 $f) GGML_HIP_PM4_DEBUG=2 $B/llama-completion -m $M -p "$PR" -n 16 --temp 0 -fa on -ngl 99 -no-cnv 2>&1 | grep -E "pm4|tape" | sort | uniq -c | sort -rn | head -12; done ;;
  abab) for c in "0 0" "1 0" "0 1" "1 1" "1 1" "0 1" "1 0" "0 0"; do set -- $c
          r=$(env $(cfg $1 $2) $B/llama-bench -m $M -p 0 -n 64 -fa 1 -ngl 99 -r 3 2>&1 | grep -E "tg64" | awk -F'|' '{print $(NF-1)}')
          echo "PM4=$1 FUSE=$2 tg64 $r"; done ;;
esac
