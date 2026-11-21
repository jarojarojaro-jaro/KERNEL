#!/bin/bash
# Kernel diag 2026-11-21 (Gemini quota out): why DSpark is slower than plain. Arms: dspark7 PM4=1 DEBUG=2 (refusal reasons),
# dspark7 PM4=0, dspark n-max 3 PM4=0. FUSE+FUSE2+NOBLAS on, FUSE3 off. AD-Q4_K.
set -u
B=$HOME/wt/upstream-inkling/build-hip/bin; export LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib GGML_HIP_INK_FUSE=1 GGML_HIP_INK_FUSE2=1 GGML_HIP_INK_NOBLAS=1
M=$HOME/models/inkling/Inkling-2-Mini-Uncensored-AD-Q4_K.gguf; D=$HOME/models/inkling/dspark-Inkling-2-Mini-Q8_0.gguf
P1="GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0 GGML_HIP_PM4_DEBUG=2"
for arm in "pm4dbg-n7|$P1|7" "nopm4-n7|GGML_HIP_PM4=0|7" "nopm4-n3|GGML_HIP_PM4=0|3"; do
  IFS='|' read name envs nmax <<< "$arm"
  env $envs $B/llama-server -m $M -md $D --spec-type draft-dspark --spec-draft-n-max $nmax -ngl 99 -fa on -c 32768 --port 18794 --jinja > /tmp/ink-d7-$name.log 2>&1 &
  pid=$!; for i in $(seq 180); do curl -fs localhost:18794/health >/dev/null && break; kill -0 $pid 2>/dev/null || break; sleep 1; done
  python3 ~/turbo-jobs/xbench.py 18794 ~/turbo/tests ink-d7-$name | grep -E "Q4|Q6|L2048"
  kill -TERM $pid; for i in $(seq 60); do kill -0 $pid 2>/dev/null || break; sleep 1; done; kill -KILL $pid 2>/dev/null
  grep -E "draft acceptance" /tmp/ink-d7-$name.log | tail -1 | cut -c40-
  grep -E "ggml_hip_pm4" /tmp/ink-d7-$name.log | grep -vE "guard|tape: " | sed -E 's/[0-9]+ nodes/N nodes/; s/[0-9.]+ ms/X ms/g' | cut -c1-200 | sort | uniq -c | sort -rn | head -8
done
