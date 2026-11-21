#!/bin/bash
# Inkling 2 Mini baseline on the XTX (inside run-jobs.sh): stock PR #32695 build (6196d98), AtomicChat uncensored AD-Q4_K
# (+ unsloth DSpark Q8_0 drafter). bench = llama-bench tg64 / pp512 / pp2048; serve = llama-server on 18794 without and with
# DSpark, xbench-style chat (copy tasks T=0, story T=0.7, long 2k/8k), then stop.
set -u
B=${INK_B:-$HOME/wt/upstream-master/build-hip/bin}; R=/opt/rocm/core-10.0/lib; export LD_LIBRARY_PATH=$B:$R GGML_HIP_PM4=${GGML_HIP_PM4:-0}
M=${INK_M:-$HOME/models/inkling/Inkling-2-Mini-UD-Q4_K_XL.gguf}; D=~/models/inkling/dspark-Inkling-2-Mini-Q8_0.gguf
case ${1:-} in
  bench) $B/llama-bench -m $M -p 512,2048 -n 64 -fa 1 -ngl 99 -r 3 2>&1 | grep -E "model|pp|tg|error" ;;
  serve) for arm in plain dspark; do
           extra=(); [ $arm = dspark ] && extra=(-md $D --spec-type draft-dspark)
           $B/llama-server -m $M "${extra[@]}" -ngl 99 -fa on -c 32768 --port 18794 --jinja > /tmp/ink-${INK_TAG:-x}-$arm.log 2>&1 &
           pid=$!; for i in $(seq 180); do curl -fs localhost:18794/health >/dev/null && break; sleep 1; done
           curl -fs localhost:18794/health >/dev/null || { echo "$arm: server did not start"; tail -5 /tmp/ink-${INK_TAG:-x}-$arm.log; kill $pid; continue; }
           python3 ~/turbo-jobs/xbench.py 18794 ~/turbo/tests ink-${INK_TAG:-x}-$arm
           grep -iE "draft acceptance|n_drafted|accept" /tmp/ink-${INK_TAG:-x}-$arm.log | tail -2
           kill -TERM $pid; for i in $(seq 60); do kill -0 $pid 2>/dev/null || break; sleep 1; done; kill -KILL $pid 2>/dev/null
         done ;;
esac
