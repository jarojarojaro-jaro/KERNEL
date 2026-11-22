#!/bin/bash
# K-001 prefill regression bisect (inside run-jobs.sh): llama-bench pp512/pp2048 (q4_0 KV, ub 2048, FA, PM4 off) for
# the bisect builds (~/wt/duo-bisect-<sha>/bin, bisect_build.sh), the r3-r7 OLD snapshot and the current duo build,
# two rounds in reversed order (drift cancels).
set -u
R=/opt/rocm/core-10.0/lib; M=~/models/orca/Qwen3.8-27B-Uncensored-Q4_K_M.gguf; export GGML_HIP_PM4=0
declare -A B=([old]=$HOME/qwen-opt/k001/hash-inst/bin [head]=$HOME/wt/l1-cachesave/build-hip/bin)
ORDER="old 9937409 556ad79 a557fc3 5ff6a15 0bb43ee head"
for s in $ORDER; do [ -n "${B[$s]:-}" ] || B[$s]=$HOME/wt/duo-bisect-$s/bin; done
REV=$(echo $ORDER | tr ' ' '\n' | tac | tr '\n' ' ')
for s in $ORDER $REV; do b=${B[$s]}
    echo "$s $(LD_LIBRARY_PATH=$b:$R $b/llama-bench -m $M -p 512,2048 -n 0 -fa 1 -ngl 99 -ctk q4_0 -ctv q4_0 -ub 2048 -r 3 2>&1 | grep -E 'pp[0-9]' | awk -F'|' '{printf "%s %s; ", $(NF-2), $(NF-1)}')"
done
