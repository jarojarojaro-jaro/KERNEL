#!/bin/bash
# Gemini ink-r4 gate (inside run-jobs.sh): INK_NOBLAS (no rocBLAS in the n=1 graph -> PM4 tape) + PM4 exit fix + DSpark padded
# vocab. All with INK_FUSE=1 INK_FUSE2=1. dbg = tape build stats; md5 = PM4 0/1 x NOBLAS 0/1; abab = tg64 ABBA PM4 x NOBLAS;
# serve = AD-Q4_K server plain/DSpark (+ n-max 7) with PM4+NOBLAS
set -u
B=$HOME/wt/upstream-inkling/build-hip/bin; export LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib GGML_HIP_INK_FUSE=1 GGML_HIP_INK_FUSE2=1
M=$HOME/models/inkling/Inkling-2-Mini-Uncensored-AD-Q4_K.gguf; D=$HOME/models/inkling/dspark-Inkling-2-Mini-Q8_0.gguf
P0="GGML_HIP_PM4=0"; P1="GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0"
PR="Explain in three sentences why the sky is blue, then list five prime numbers."
cfg() { [ $1 = 1 ] && echo "$P1 GGML_HIP_INK_NOBLAS=$2" || echo "$P0 GGML_HIP_INK_NOBLAS=$2"; }
case ${1:-} in
  dbg) for nb in 0 1; do echo "== NOBLAS=$nb"; env $(cfg 1 $nb) GGML_HIP_PM4_DEBUG=2 $B/llama-completion -m $M -p "$PR" -n 16 --temp 0 -fa on -ngl 99 -no-cnv 2>&1 | grep -E "pm4|tape" | sed -E 's/[0-9]+ nodes/N nodes/' | cut -c1-200 | sort | uniq -c | sort -rn | head -8; done ;;
  md5) for c in "0 0" "0 1" "1 1"; do set -- $c
         out=$(env $(cfg $1 $2) $B/llama-completion -m $M -p "$PR" -n 128 --temp 0 --seed 42 -fa on -ngl 99 -no-cnv --no-display-prompt 2>/dev/null)
         echo "PM4=$1 NOBLAS=$2 md5=$(printf '%s' "$out" | md5sum | cut -c1-8) len=${#out}"; done ;;
  abab) for c in "0 0" "0 1" "1 1" "1 1" "0 1" "0 0"; do set -- $c
          r=$(env $(cfg $1 $2) $B/llama-bench -m $M -p 0 -n 64 -fa 1 -ngl 99 -r 3 2>&1 | grep tg64 | awk -F'|' '{print $(NF-1)}')
          echo "PM4=$1 NOBLAS=$2 tg64 $r"; done ;;
  serve) export $P1 GGML_HIP_INK_NOBLAS=1
         for arm in plain dspark dspark7; do
           extra=(); [ $arm = dspark ] && extra=(-md $D --spec-type draft-dspark); [ $arm = dspark7 ] && extra=(-md $D --spec-type draft-dspark --spec-draft-n-max 7)
           $B/llama-server -m $M "${extra[@]}" -ngl 99 -fa on -c 32768 --port 18794 --jinja > /tmp/ink-r4-$arm.log 2>&1 &
           pid=$!; for i in $(seq 180); do curl -fs localhost:18794/health >/dev/null && break; kill -0 $pid 2>/dev/null || break; sleep 1; done
           if curl -fs localhost:18794/health >/dev/null; then python3 ~/turbo-jobs/xbench.py 18794 ~/turbo/tests ink-r4-$arm
             grep -iE "draft acceptance|accept" /tmp/ink-r4-$arm.log | tail -2
           else echo "$arm: server did not start"; grep " E " /tmp/ink-r4-$arm.log | head -3; fi
           kill -TERM $pid 2>/dev/null; for i in $(seq 60); do kill -0 $pid 2>/dev/null || break; sleep 1; done; kill -KILL $pid 2>/dev/null
         done ;;
esac
