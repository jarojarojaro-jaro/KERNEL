#!/bin/bash
# Gemini ink-r15 gate: LLAMA_INK_SRV_FAST=1 (server plain-step overhead: stable graph, device top-k, DSpark tap skip). KV q4_0.
set -u
B=$HOME/wt/upstream-inkling/build-hip/bin; export LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib
BASE="GGML_HIP_INK_FUSE=1 GGML_HIP_INK_FUSE2=1 GGML_HIP_INK_FUSE3=1 GGML_HIP_INK_NOBLAS=1"
R13="$BASE GGML_HIP_INK_STABLE_GRAPH=1 GGML_HIP_INK_PLANAR_Q8=1 GGML_HIP_INK_F4_ROUTER=1 GGML_HIP_INK_F4_COMBINE=1 GGML_HIP_INK_F4_QKVCONV=1 GGML_HIP_INK_F4_LOOPMSG=1 GGML_HIP_INK_LOADFIRST=1"
R14="$R13 GGML_HIP_INK_NT=1"
M=$HOME/models/inkling/Inkling-2-Mini-Uncensored-AD-Q4_K.gguf; D=$HOME/models/inkling/dspark-Inkling-2-Mini-Q8_0.gguf
T=$HOME/wt/lfm3-prof/wikitext-2-raw/wiki.test.raw; cd ~/qwen-opt/inkling; KV="-ctk q4_0 -ctv q4_0"
case ${1:-} in
  kld) P=(-f $T -c 2048 --chunks 4 -b 2048 -ub 512 -ngl 99 -fa on $KV)
       for e in "r13|$R13" "r14|$R14"; do IFS='|' read n v <<< "$e"
         env GGML_HIP_PM4=0 $v $B/llama-perplexity -m $M "${P[@]}" --kl-divergence-base ink-q4kv.kld --kl-divergence > kld-r15-$n.log 2>&1
         echo "$n: $(grep -E "^Mean +KLD|^Maximum KLD|^Same top p" kld-r15-$n.log | tr -s ' ' | tr '\n' ';')"; done
       env GGML_HIP_PM4=0 $R14 $B/test-backend-ops test -o MUL_MAT_ID 2>&1 | grep -E "passed|FAIL" | tail -2 ;;
  tg) for e in "base|$BASE" "r13|$R13" "r14|$R14" "r14|$R14"; do IFS='|' read n v <<< "$e"
        echo "$n $(env GGML_HIP_PM4=0 $v $B/llama-bench -m $M -p 0 -n 128 -fa 1 -ngl 99 $KV -r 3 2>&1 | grep tg128 | awk -F'|' '{print $(NF-1)}')"; done ;;
  serve) for a in "r15-fast-ds|LLAMA_INK_SRV_FAST=1 LLAMA_SPEC_CTL=0|-md $D --spec-type draft-dspark --spec-draft-n-max 7 --spec-draft-sampling probabilistic" "r15-fast-ctl-ngds|LLAMA_INK_SRV_FAST=1 LLAMA_SPEC_CTL=1|-md $D --spec-type ngram-simple,draft-dspark --spec-draft-n-max 7 --spec-draft-sampling probabilistic" "r15-slow-ctl-ngds|LLAMA_SPEC_CTL=1|-md $D --spec-type ngram-simple,draft-dspark --spec-draft-n-max 7 --spec-draft-sampling probabilistic" "r14-ctl-ds|LLAMA_SPEC_CTL=1|-md $D --spec-type draft-dspark --spec-draft-n-max 7 --spec-draft-sampling probabilistic" "r14-ds|LLAMA_SPEC_CTL=0|-md $D --spec-type draft-dspark --spec-draft-n-max 7 --spec-draft-sampling probabilistic"; do
           IFS='|' read name ctl extra <<< "$a"
           env GGML_HIP_PM4=0 $R14 $ctl $B/llama-server -m $M $extra $KV -ctkd q4_0 -ctvd q4_0 -ngl 99 -fa on -c 16384 --port 18794 --jinja > /tmp/ink-$name.log 2>&1 &
           pid=$!; for i in $(seq 180); do curl -fs localhost:18794/health >/dev/null && break; kill -0 $pid 2>/dev/null || break; sleep 1; done
           if curl -fs localhost:18794/health >/dev/null; then python3 ~/turbo-jobs/xbench.py 18794 ~/turbo/tests ink-$name | grep -E "Q1|Q4|Q6|L2048|L8192"; else echo "$name: did not start"; grep " E " /tmp/ink-$name.log | head -3; fi
           kill -TERM $pid 2>/dev/null; for i in $(seq 60); do kill -0 $pid 2>/dev/null || break; sleep 1; done; kill -KILL $pid 2>/dev/null
           grep -E "draft acceptance|spec_ctl" /tmp/ink-$name.log | tail -2 | cut -c30-200
         done ;;
esac
