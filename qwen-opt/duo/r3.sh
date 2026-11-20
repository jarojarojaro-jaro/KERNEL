#!/bin/bash
# Duo r3 (inside run-jobs.sh): Gemini's FA masked-tile fix (556ad79) on the XTX. test = masked-tail test-backend-ops +
# FA regression; bench = llama-bench pp512/pp2048/tg64 with the fix vs the pre-fix snapshot (~/qwen-opt/k001/hash-inst).
set -u
NEW=~/wt/l1-cachesave/build-hip/bin; OLD=~/qwen-opt/k001/hash-inst/bin; R=/opt/rocm/core-10.0/lib
M=~/models/orca/Qwen3.8-27B-Uncensored-Q4_K_M.gguf; export GGML_HIP_PM4=0
case ${1:-} in
  test) for kv in 0 1; do echo "== KVQ_OFF=$kv"
          env GGML_HIP_KVQ_OFF=$kv LD_LIBRARY_PATH=$NEW:$R timeout 280 $NEW/test-backend-ops test -o FLASH_ATTN_EXT_MASKED_TAIL 2>&1 | grep -E "FAIL|OK|passed|tests" | tail -4; done
        echo "== FA regression (hsk 256, q4_0)"
        LD_LIBRARY_PATH=$NEW:$R timeout 280 $NEW/test-backend-ops test -o FLASH_ATTN_EXT -p "hsk=256.*type_K=q4_0" 2>&1 | grep -E "FAIL|passed|tests" | tail -4 ;;
  bench) for b in OLD NEW OLD NEW; do B=${!b}
          echo "$b $(LD_LIBRARY_PATH=$B:$R $B/llama-bench -m $M -p 512,2048 -n 64 -fa on -ngl 99 -ctk q4_0 -ctv q4_0 -ub 2048 -r 2 2>&1 | grep -E '(pp|tg)[0-9]' | awk -F'|' '{printf "%s %s; ", $(NF-2), $(NF-1)}')"; done ;;
esac
case ${1:-} in
  kld) cd ~/qwen-opt/duo; T=~/wt/lfm3-prof/wikitext-2-raw/wiki.test.raw
       for ub in 5 512; do
         env LD_LIBRARY_PATH=$NEW:$R GGML_HIP_PM4=0 $NEW/llama-perplexity -m $M -f $T -c 8192 --chunks 2 -b 8192 -ngl 999 -fa on -ub $ub -ctk q4_0 -ctv q4_0 --kl-divergence-base ref.kld --kl-divergence > fix$ub.log 2>&1
         [ -f base$ub.log ] || env LD_LIBRARY_PATH=$OLD:$R GGML_HIP_PM4=0 $OLD/llama-perplexity -m $M -f $T -c 8192 --chunks 2 -b 8192 -ngl 999 -fa on -ub $ub -ctk q4_0 -ctv q4_0 --kl-divergence-base ref.kld --kl-divergence > base$ub.log 2>&1
         echo "== ub $ub"; python3 ~/qwen-opt/tools/kld_gate.py compare base$ub.log fix$ub.log
       done ;;
  tailfail) LD_LIBRARY_PATH=$NEW:$R timeout 280 $NEW/test-backend-ops test -o FLASH_ATTN_EXT_MASKED_TAIL 2>&1 | grep -vE "^\s*$" | grep -iE "FAIL|err|nb=|tail" | head -30 ;;
esac
