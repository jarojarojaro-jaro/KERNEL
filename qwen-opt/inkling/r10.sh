#!/bin/bash
# Gemini ink-r8 gate (inside run-jobs.sh): FUSE3 fix (looped-layer indexing), PM4 scratch-free verify FA + refusal cache,
# DSpark probabilistic draft sampling. kld = FUSE3 0/1 vs all-off ink.kld; ab = tg64 + md5; serve = plain / DSpark n7 PM4 1/0
# (+ probabilistic) with FUSE+FUSE2+FUSE3+NOBLAS
set -u
B=$HOME/wt/upstream-inkling/build-hip/bin; export LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib GGML_HIP_INK_FUSE=1 GGML_HIP_INK_FUSE2=1 GGML_HIP_INK_NOBLAS=1
M=$HOME/models/inkling/Inkling-2-Mini-Uncensored-AD-Q4_K.gguf; D=$HOME/models/inkling/dspark-Inkling-2-Mini-Q8_0.gguf
T=$HOME/wt/lfm3-prof/wikitext-2-raw/wiki.test.raw; cd ~/qwen-opt/inkling
P0="GGML_HIP_PM4=0"; P1="GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0"
PR="Explain in three sentences why the sky is blue, then list five prime numbers."
case ${1:-} in
  kld) for f3 in 1 0; do env $P0 GGML_HIP_INK_FUSE3=$f3 $B/llama-perplexity -m $M -f $T -c 2048 --chunks 4 -b 2048 -ub 512 -ngl 99 -fa on --kl-divergence-base ink.kld --kl-divergence > kld-r8-$f3.log 2>&1
         echo "FUSE3=$f3: $(grep -E "^Mean +KLD|^Same top p|^Mean PPL\(Q\)/PPL|^Maximum KLD" kld-r8-$f3.log | tr -s ' ' | tr '\n' ';')"; done ;;
  ab) for c in "$P1 GGML_HIP_INK_FUSE3=1" "$P0 GGML_HIP_INK_FUSE3=1"; do
        out=$(env $c $B/llama-completion -m $M -p "$PR" -n 128 --temp 0 --seed 42 -fa on -ngl 99 -no-cnv --no-display-prompt 2>/dev/null)
        echo "${c%% *} md5=$(printf '%s' "$out" | md5sum | cut -c1-8) | ${out:0:100}" | tr '\n' ' '; echo; done
      for c in "$P1 GGML_HIP_INK_FUSE3=0" "$P1 GGML_HIP_INK_FUSE3=1" "$P1 GGML_HIP_INK_FUSE3=1" "$P1 GGML_HIP_INK_FUSE3=0"; do
        echo "${c%% *} ${c##* } tg64 $(env $c $B/llama-bench -m $M -p 0 -n 64 -fa 1 -ngl 99 -r 5 2>&1 | grep tg64 | awk -F'|' '{print $(NF-1)}')"; done ;;
  serve) export GGML_HIP_INK_FUSE3=1 GGML_HIP_PM4_DEBUG=1
         export LLAMA_SPEC_CTL=${LLAMA_SPEC_CTL:-1}
         for arm in "ctl-n7-prob|$P0|-md $D --spec-type draft-dspark --spec-draft-n-max 7 --spec-draft-sampling probabilistic -ub ${INK_UB:-512}" "ctl-n7-ng-prob|$P0|-md $D --spec-type ngram-simple,draft-dspark --spec-draft-n-max 7 --spec-draft-sampling probabilistic -ub ${INK_UB:-512}"; do
           IFS='|' read name envs extra <<< "$arm"
           env $envs $B/llama-server -m $M $extra -ngl 99 -fa on -c ${INK_CTX:-16384} --port 18794 --jinja > /tmp/ink-r10-${INK_TAG:-a}-$name.log 2>&1 &
           pid=$!; for i in $(seq 180); do curl -fs localhost:18794/health >/dev/null && break; kill -0 $pid 2>/dev/null || break; sleep 1; done
           if curl -fs localhost:18794/health >/dev/null; then python3 ~/turbo-jobs/xbench.py 18794 ~/turbo/tests ink-r10-${INK_TAG:-a}-$name | grep -E "Q1|Q4|Q6|L2048|L8192"
           else echo "$name: server did not start"; grep " E " /tmp/ink-r10-${INK_TAG:-a}-$name.log | head -3; fi
           kill -TERM $pid 2>/dev/null; for i in $(seq 60); do kill -0 $pid 2>/dev/null || break; sleep 1; done; kill -KILL $pid 2>/dev/null
           grep -E "draft acceptance" /tmp/ink-r10-${INK_TAG:-a}-$name.log | tail -1 | cut -c40-; grep "pm4: summary" /tmp/ink-r10-${INK_TAG:-a}-$name.log | cut -c1-200
         done ;;
  serve0) export GGML_HIP_INK_FUSE3=0 GGML_HIP_PM4_DEBUG=1
         env $P0 $B/llama-server -m $M -md $D --spec-type draft-dspark --spec-draft-n-max 7 --spec-draft-sampling probabilistic -ngl 99 -fa on -c 16384 --port 18794 --jinja > /tmp/ink-r10-f3off.log 2>&1 &
         pid=$!; for i in $(seq 180); do curl -fs localhost:18794/health >/dev/null && break; kill -0 $pid 2>/dev/null || break; sleep 1; done
         if curl -fs localhost:18794/health >/dev/null; then python3 ~/turbo-jobs/xbench.py 18794 ~/turbo/tests ink-r8b-f3off-prob | grep -E "Q1|Q4|Q6|L2048|L8192"; else echo "f3off: server did not start"; grep " E " /tmp/ink-r10-f3off.log | head -3; fi
         kill -TERM $pid 2>/dev/null; for i in $(seq 60); do kill -0 $pid 2>/dev/null || break; sleep 1; done; kill -KILL $pid 2>/dev/null
         grep -E "draft acceptance" /tmp/ink-r10-f3off.log | tail -1 | cut -c40- ;;
esac
