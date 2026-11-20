#!/bin/bash
# Duo r1 (inside run-jobs.sh): GGML_HIP_MMVQ_TURBO (Gemini r1, Turbo-style RDNA3 MMVQ for Q4_K/Q6_K, ncols 1..8) vs the
# production MMVQ on the XTX. Build: ~/wt/l1-cachesave/build-hip (branch duo). Model Qwen3.8-27B-Uncensored Q4_K_M.
#   bench: llama-bench tg64, PM4 as in production, TURBO 0/1/0/1 (ABAB)
#   kld:   wikitext-2 -c 8192 --chunks 2, ref = f16 KV (stock kernels, -ub 512); arms q4_0 KV with -ub 1 and -ub 5
#          (MMVQ widths 1 and 5), TURBO 0 vs 1; gate kld_gate.py compare base cand
set -u
cd ~/qwen-opt/duo
B=~/wt/l1-cachesave/build-hip/bin; export LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib
M=~/models/orca/Qwen3.8-27B-Uncensored-Q4_K_M.gguf; T=~/wt/lfm3-prof/wikitext-2-raw/wiki.test.raw
PM=(GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0)
C=(-m "$M" -f "$T" -c 8192 --chunks 2 -b 8192 -ngl 999 -fa on)
run() { local name=$1; shift; echo "$(date +%T) $name"; env GGML_HIP_PM4=0 "$@" > "$name.log" 2>&1; echo "$(date +%T) $name rc=$? $(grep -E 'Mean    KLD|Same top p|Final estimate' "$name.log" | tr -s ' ' | tr '\n' ' ')"; }
case ${1:-} in
  bench) for t in ${ARMS:-0 1 0 1}; do
           echo "TURBO=$t $(env "${PM[@]}" GGML_HIP_MMVQ_TURBO=$t $B/llama-bench -m $M -p 0 -n 64 -fa on -ngl 99 -r 3 2>&1 | grep -E 'tg64|error' | tr -s ' ')"
         done ;;
  ref)   run ref "$B/llama-perplexity" "${C[@]}" -ub 512 -ctk f16 -ctv f16 --kl-divergence-base ref.kld ;;
  arms)  for ub in ${UBS:-5 1}; do
           run base$ub env GGML_HIP_MMVQ_TURBO=0 "$B/llama-perplexity" "${C[@]}" -ub $ub -ctk q4_0 -ctv q4_0 --kl-divergence-base ref.kld --kl-divergence
           run cand$ub env GGML_HIP_MMVQ_TURBO=${CAND:-1} "$B/llama-perplexity" "${C[@]}" -ub $ub -ctk q4_0 -ctv q4_0 --kl-divergence-base ref.kld --kl-divergence
           python3 ~/qwen-opt/tools/kld_gate.py compare base$ub.log cand$ub.log | tee -a gate.txt
         done ;;
esac
