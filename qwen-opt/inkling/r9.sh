#!/bin/bash
# Gemini ink-r9 gate (inside run-jobs.sh): GGML_HIP_INK_MEGA (one-kernel MoE: router, top-8, gate_up, SwiGLU, down, combine)
# on top of FUSE+FUSE2+FUSE3+NOBLAS. tbo = correctness + perf of INK_MOE_MEGA; kld = MEGA 0/1 vs all-off ink.kld; tg = tg64
# + pp5/pp8 (verify-sized) MEGA 0/1 with PM4; serve = DSpark n7 probabilistic with MEGA (PM4 on)
set -u
B=$HOME/wt/upstream-inkling/build-hip/bin; export LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib GGML_HIP_INK_FUSE=1 GGML_HIP_INK_FUSE2=1 GGML_HIP_INK_FUSE3=1 GGML_HIP_INK_NOBLAS=1
M=$HOME/models/inkling/Inkling-2-Mini-Uncensored-AD-Q4_K.gguf; D=$HOME/models/inkling/dspark-Inkling-2-Mini-Q8_0.gguf
T=$HOME/wt/lfm3-prof/wikitext-2-raw/wiki.test.raw; cd ~/qwen-opt/inkling
P0="GGML_HIP_PM4=0"; P1="GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0"
case ${1:-} in
  tbo) env $P0 GGML_HIP_INK_MEGA=1 $B/test-backend-ops -o INK_MOE_MEGA 2>&1 | grep -E "FAIL|passed" | head -8
       for mg in 0 1; do echo "== perf MEGA=$mg"; env $P0 GGML_HIP_INK_MEGA=$mg $B/test-backend-ops perf -o INK_MOE_MEGA 2>&1 | grep -E "us/run" | cut -c1-160 | head -8; done ;;
  kld) for mg in 1; do env $P0 GGML_HIP_INK_MEGA=$mg $B/llama-perplexity -m $M -f $T -c 2048 --chunks 4 -b 2048 -ub 512 -ngl 99 -fa on --kl-divergence-base ink.kld --kl-divergence > kld-r9.log 2>&1
       echo "MEGA=$mg: $(grep -E "^Mean +KLD|^Same top p|^Mean PPL\(Q\)/PPL|^Maximum KLD" kld-r9.log | tr -s ' ' | tr '\n' ';')"; done ;;
  tg) for c in "$P1 GGML_HIP_INK_MEGA=0" "$P1 GGML_HIP_INK_MEGA=1" "$P1 GGML_HIP_INK_MEGA=1" "$P1 GGML_HIP_INK_MEGA=0"; do
        echo "${c##* } $(env $c $B/llama-bench -m $M -p 8 -n 64 -ub 8 -b 8 -fa 1 -ngl 99 -r 3 2>&1 | grep -E "pp8|tg64" | awk -F'|' '{print $(NF-2), $(NF-1)}' | tr '\n' ' ')"; done ;;
  serve) export $P1 GGML_HIP_PM4_DEBUG=1 GGML_HIP_INK_MEGA=1
         $B/llama-server -m $M -md $D --spec-type draft-dspark --spec-draft-n-max 7 --spec-draft-sampling probabilistic -ngl 99 -fa on -c 32768 --port 18794 --jinja > /tmp/ink-r9.log 2>&1 &
         pid=$!; for i in $(seq 180); do curl -fs localhost:18794/health >/dev/null && break; kill -0 $pid 2>/dev/null || break; sleep 1; done
         if curl -fs localhost:18794/health >/dev/null; then python3 ~/turbo-jobs/xbench.py 18794 ~/turbo/tests ink-r9-mega | grep -E "Q1|Q4|Q6|L2048|L8192"
         else echo "server did not start"; grep " E " /tmp/ink-r9.log | head -3; fi
         kill -TERM $pid 2>/dev/null; for i in $(seq 60); do kill -0 $pid 2>/dev/null || break; sleep 1; done; kill -KILL $pid 2>/dev/null
         grep -E "draft acceptance" /tmp/ink-r9.log | tail -1 | cut -c40-; grep "pm4: summary" /tmp/ink-r9.log | cut -c1-200 ;;
esac
