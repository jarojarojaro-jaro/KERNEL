#!/bin/bash
# K-125 (inside run-jobs.sh): KLD of the kvq attention path vs the stock kernel for Qwen3.8-27B-Uncensored Q4_K_M on the
# XTX. Build k001-log (topka-q70 3191b25f4 + GGML_HIP_KVQ_OFF switch, off unless set, + env-gated K-001 log). Ref = f16 KV;
# base = q4_0 KV with kvq OFF (stock vec/tile kernel); cand = q4_0 KV with kvq (production path); cand2 = repeat
# (determinism). wikitext-2 test, -c 8192, 2 chunks (8192 scored tokens), -ub 5 so attention runs the verify-size
# kernels (kvq takes <= 16 rows). PM4 off. Gate: kld_gate.py compare base cand (k = 2, tail 1.25).
set -u
cd ~/qwen-opt/k125
B=~/qwen-opt/k001/inst/bin; export LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib GGML_HIP_PM4=0
M=~/models/orca/Qwen3.8-27B-Uncensored-Q4_K_M.gguf; T=~/wt/lfm3-prof/wikitext-2-raw/wiki.test.raw
C=(-m "$M" -f "$T" -c 8192 --chunks 2 -b 8192 -ub 5 -ngl 999 -fa on)
run() { local name=$1; shift; echo "$(date +%T) $name"; "$B/llama-perplexity" "${C[@]}" "$@" > "$name.log" 2>&1; echo "$(date +%T) $name rc=$?"; }
case ${1:-} in
  ref)   run ref -ctk f16 -ctv f16 --kl-divergence-base ref.kld ;;
  arms)  GGML_HIP_KVQ_OFF=1 run base -ctk q4_0 -ctv q4_0 --kl-divergence-base ref.kld --kl-divergence
         run cand  -ctk q4_0 -ctv q4_0 --kl-divergence-base ref.kld --kl-divergence
         run cand2 -ctk q4_0 -ctv q4_0 --kl-divergence-base ref.kld --kl-divergence
         python3 ~/qwen-opt/tools/kld_gate.py compare base.log cand.log | tee gate.txt
         python3 ~/qwen-opt/tools/kld_gate.py compare cand.log cand2.log | tee -a gate.txt
         rm -f ref.kld ;;
esac
