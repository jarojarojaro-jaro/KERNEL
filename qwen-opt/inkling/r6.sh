#!/bin/bash
# Gemini ink-r6 gate (inside run-jobs.sh): DSpark Inkling2 drafter + PM4 counters/lazy exec; FUSE3 stays OFF (r5: KLD 4.68).
# tbo = test-backend-ops for the INK_* fused ops with all fusion switches on (finds the FUSE3 bug); pm4 = tg64 lazy vs eager +
# counters; serve = AD-Q4_K server plain / DSpark default / DSpark n-max 7 with PM4+NOBLAS+FUSE+FUSE2
set -u
B=$HOME/wt/upstream-inkling/build-hip/bin; export LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib GGML_HIP_INK_FUSE=1 GGML_HIP_INK_FUSE2=1 GGML_HIP_INK_NOBLAS=1
M=$HOME/models/inkling/Inkling-2-Mini-Uncensored-AD-Q4_K.gguf; D=$HOME/models/inkling/dspark-Inkling-2-Mini-Q8_0.gguf
P1="GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0"
case ${1:-} in
  tbo) for op in INK_MIX INK_CTRL_RMS_NORM INK_GATED_MERGE_RMS_NORM INK_SITU INK_CONVOLVE INK_REL_BIAS_MASK; do
         r=$(env GGML_HIP_PM4=0 GGML_HIP_INK_FUSE3=1 $B/test-backend-ops -o $op 2>&1); echo "$op: $(echo "$r" | grep -cE "FAIL") FAIL, $(echo "$r" | grep -oE "[0-9]+/[0-9]+ tests passed" | head -1)"
         echo "$r" | grep -E "FAIL" | head -3 | cut -c1-200; done ;;
  pm4) for lz in 1 0 1 0; do echo "LAZY=$lz $(env $P1 GGML_HIP_PM4_LAZY_EXEC=$lz GGML_HIP_PM4_DEBUG=1 $B/llama-bench -m $M -p 0 -n 64 -fa 1 -ngl 99 -r 5 2>&1 | grep -E "tg64|ggml_hip_pm4:" | awk -F'|' '{print ($0 ~ /tg64/) ? $(NF-1) : $0}' | tr '\n' ' ' | cut -c1-400)"; done ;;
  serve) export $P1 GGML_HIP_PM4_DEBUG=1
         for arm in plain dspark dspark7; do
           extra=(); [ $arm = dspark ] && extra=(-md $D --spec-type draft-dspark); [ $arm = dspark7 ] && extra=(-md $D --spec-type draft-dspark --spec-draft-n-max 7)
           $B/llama-server -m $M "${extra[@]}" -ngl 99 -fa on -c 32768 --port 18794 --jinja > /tmp/ink-r6-$arm.log 2>&1 &
           pid=$!; for i in $(seq 180); do curl -fs localhost:18794/health >/dev/null && break; kill -0 $pid 2>/dev/null || break; sleep 1; done
           if curl -fs localhost:18794/health >/dev/null; then python3 ~/turbo-jobs/xbench.py 18794 ~/turbo/tests ink-r6-$arm
           else echo "$arm: server did not start"; grep " E " /tmp/ink-r6-$arm.log | head -3; fi
           kill -TERM $pid 2>/dev/null; for i in $(seq 60); do kill -0 $pid 2>/dev/null || break; sleep 1; done; kill -KILL $pid 2>/dev/null
           grep -E "draft acceptance|DFlash padded|DFlash extract|ggml_hip_pm4:" /tmp/ink-r6-$arm.log | grep -v guard | tail -4 | cut -c1-220
         done ;;
esac
