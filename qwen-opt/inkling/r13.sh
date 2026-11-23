#!/bin/bash
# Gemini ink-r11 gate (STABLE_GRAPH, FUSE4, PLANAR_Q8), KV q4_0 everywhere (owner 2026-11-23). base = FUSE+FUSE2+FUSE3+NOBLAS.
set -u
B=$HOME/wt/upstream-inkling/build-hip/bin; export LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib GGML_HIP_INK_FUSE=1 GGML_HIP_INK_FUSE2=1 GGML_HIP_INK_FUSE3=1 GGML_HIP_INK_NOBLAS=1
M=$HOME/models/inkling/Inkling-2-Mini-Uncensored-AD-Q4_K.gguf; D=$HOME/models/inkling/dspark-Inkling-2-Mini-Q8_0.gguf
T=$HOME/wt/lfm3-prof/wikitext-2-raw/wiki.test.raw; cd ~/qwen-opt/inkling; KV="-ctk q4_0 -ctv q4_0"
P0="GGML_HIP_PM4=0"; P1="GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0"
ARMS=("base|" "stable|GGML_HIP_INK_STABLE_GRAPH=1" "f4router|GGML_HIP_INK_F4_ROUTER=1" "f4combine|GGML_HIP_INK_F4_COMBINE=1" "f4qkvconv|GGML_HIP_INK_F4_QKVCONV=1" "f4loopmsg|GGML_HIP_INK_F4_LOOPMSG=1" "planar|GGML_HIP_INK_PLANAR_Q8=1" "loadfirst|GGML_HIP_INK_LOADFIRST=1" "all|GGML_HIP_INK_STABLE_GRAPH=1 GGML_HIP_INK_FUSE4=1 GGML_HIP_INK_PLANAR_Q8=1 GGML_HIP_INK_LOADFIRST=1")
case ${1:-} in
  kld) P=(-f $T -c 2048 --chunks 4 -b 2048 -ub 512 -ngl 99 -fa on $KV)
       env $P0 $B/llama-perplexity -m $M "${P[@]}" --kl-divergence-base ink-q4kv.kld > kld-r13-base.log 2>&1; grep "Final estimate" kld-r13-base.log
       for a in "${ARMS[@]:1}"; do IFS='|' read n e <<< "$a"
         env $P0 $e $B/llama-perplexity -m $M "${P[@]}" --kl-divergence-base ink-q4kv.kld --kl-divergence > kld-r13-$n.log 2>&1
         echo "$n: $(grep -E "^Mean +KLD|^Maximum KLD|^Same top p|^Mean PPL\(Q\)/PPL" kld-r13-$n.log | tr -s ' ' | tr '\n' ';')"; done ;;
  tg) for a in "${ARMS[@]}"; do IFS='|' read n e <<< "$a"
        for pm in P0; do echo "$n $pm $(env ${!pm} $e $B/llama-bench -m $M -p 0 -n 128 -fa 1 -ngl 99 $KV -r 3 2>&1 | grep -E "tg128|error" | awk -F'|' '{print $(NF-1)}')"; done; done ;;
  serve) for a in "base|" "all|GGML_HIP_INK_STABLE_GRAPH=1 GGML_HIP_INK_FUSE4=1 GGML_HIP_INK_PLANAR_Q8=1 GGML_HIP_INK_LOADFIRST=1"; do IFS='|' read n e <<< "$a"
         for pm in P0; do name=$n-$pm
           env ${!pm} $e $B/llama-server -m $M -md $D --spec-type draft-dspark --spec-draft-n-max 7 --spec-draft-sampling probabilistic $KV -ctkd q4_0 -ctvd q4_0 -ngl 99 -fa on -c 16384 --port 18794 --jinja > /tmp/ink-r13-$name.log 2>&1 &
           pid=$!; for i in $(seq 180); do curl -fs localhost:18794/health >/dev/null && break; kill -0 $pid 2>/dev/null || break; sleep 1; done
           if curl -fs localhost:18794/health >/dev/null; then python3 ~/turbo-jobs/xbench.py 18794 ~/turbo/tests ink-r13-$name | grep -E "Q1|Q4|Q6|L2048|L8192"; else echo "$name: did not start"; grep " E " /tmp/ink-r13-$name.log | head -3; fi
           kill -TERM $pid 2>/dev/null; for i in $(seq 60); do kill -0 $pid 2>/dev/null || break; sleep 1; done; kill -KILL $pid 2>/dev/null
           grep -E "draft acceptance" /tmp/ink-r13-$name.log | tail -1 | cut -c40-160
         done; done ;;
esac
