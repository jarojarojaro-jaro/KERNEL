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
case ${1:-} in
  r4bench) for b in OLD NEW OLD NEW; do B=${!b}
          echo "$b $(LD_LIBRARY_PATH=$B:$R $B/llama-bench -m $M -p 512,2048 -n 0 -fa on -ngl 99 -ctk q4_0 -ctv q4_0 -ub 2048 -r 3 2>&1 | grep -E 'pp[0-9]' | awk -F'|' '{printf "%s %s; ", $(NF-2), $(NF-1)}')"; done
        for v in 0 1 0 1; do
          echo "GDN_FUSED=$v $(env GGML_HIP_GDN_FUSED=$v GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0 LD_LIBRARY_PATH=$NEW:$R $NEW/llama-bench -m $M -p 0 -n 64 -fa on -ngl 99 -ctk q4_0 -ctv q4_0 -r 3 2>&1 | grep -E 'tg[0-9]' | awk -F'|' '{printf "%s %s; ", $(NF-2), $(NF-1)}')"; done ;;
  r4kld) cd ~/qwen-opt/duo; T=~/wt/lfm3-prof/wikitext-2-raw/wiki.test.raw
       for ub in 1 5; do
         env LD_LIBRARY_PATH=$NEW:$R GGML_HIP_PM4=0 $NEW/llama-perplexity -m $M -f $T -c 8192 --chunks 2 -b 8192 -ngl 999 -fa on -ub $ub -ctk q4_0 -ctv q4_0 --kl-divergence-base ref.kld --kl-divergence > r4off$ub.log 2>&1
         env GGML_HIP_GDN_FUSED=1 LD_LIBRARY_PATH=$NEW:$R GGML_HIP_PM4=0 $NEW/llama-perplexity -m $M -f $T -c 8192 --chunks 2 -b 8192 -ngl 999 -fa on -ub $ub -ctk q4_0 -ctv q4_0 --kl-divergence-base ref.kld --kl-divergence > r4gdn$ub.log 2>&1
         echo "== ub $ub fix(off) vs base"; python3 ~/qwen-opt/tools/kld_gate.py compare base$ub.log r4off$ub.log | tail -2
         echo "== ub $ub GDN_FUSED=1 vs off"; python3 ~/qwen-opt/tools/kld_gate.py compare r4off$ub.log r4gdn$ub.log
       done ;;
esac
case ${1:-} in
  r5test) for o in "MUL_MAT" "GATED_DELTA_NET"; do echo "== $o"
            env GGML_HIP_MMQ_GLU=1 GGML_HIP_GDN_CHUNK=1 LD_LIBRARY_PATH=$NEW:$R timeout 280 $NEW/test-backend-ops test -o $o 2>&1 | grep -E "FAIL|passed|Backend ROCm0" | tail -4; done ;;
  r5bench) for a in "0 0" "1 0" "0 1" "1 1" "0 0" "1 0" "0 1" "1 1"; do set -- $a
            echo "GLU=$1 CHUNK=$2 $(env GGML_HIP_MMQ_GLU=$1 GGML_HIP_GDN_CHUNK=$2 LD_LIBRARY_PATH=$NEW:$R $NEW/llama-bench -m $M -p 512,2048 -n 0 -fa on -ngl 99 -ctk q4_0 -ctv q4_0 -ub 2048 -r 3 2>&1 | grep -E 'pp[0-9]' | awk -F'|' '{printf "%s %s; ", $(NF-2), $(NF-1)}')"; done ;;
  r5kld) cd ~/qwen-opt/duo; T=~/wt/lfm3-prof/wikitext-2-raw/wiki.test.raw
       env GGML_HIP_MMQ_GLU=1 GGML_HIP_GDN_CHUNK=1 LD_LIBRARY_PATH=$NEW:$R GGML_HIP_PM4=0 $NEW/llama-perplexity -m $M -f $T -c 8192 --chunks 2 -b 8192 -ngl 999 -fa on -ub 512 -ctk q4_0 -ctv q4_0 --kl-divergence-base ref.kld --kl-divergence > r5on512.log 2>&1
       echo "== ub 512 GLU+CHUNK vs fix"; python3 ~/qwen-opt/tools/kld_gate.py compare fix512.log r5on512.log ;;
esac
case ${1:-} in
  r6test) env GGML_HIP_GDN_CHUNK=1 LD_LIBRARY_PATH=$NEW:$R timeout 400 $NEW/test-backend-ops test -o GATED_DELTA_NET_LAG 2>&1 | grep -E "FAIL|passed|Backend ROCm0" | tail -4
          env GGML_HIP_GDN_CHUNK=1 LD_LIBRARY_PATH=$NEW:$R timeout 200 $NEW/test-backend-ops test -o GATED_DELTA_NET 2>&1 | grep -E "FAIL|passed|Backend ROCm0" | tail -4 ;;
  r6kld) cd ~/qwen-opt/duo; T=~/wt/lfm3-prof/wikitext-2-raw/wiki.test.raw
       env GGML_HIP_GDN_CHUNK=1 LD_LIBRARY_PATH=$NEW:$R GGML_HIP_PM4=0 $NEW/llama-perplexity -m $M -f $T -c 8192 --chunks 2 -b 8192 -ngl 999 -fa on -ub 512 -ctk q4_0 -ctv q4_0 --kl-divergence-base ref.kld --kl-divergence > r6on512.log 2>&1
       echo "== ub 512 CHUNK(lag) vs fix"; python3 ~/qwen-opt/tools/kld_gate.py compare fix512.log r6on512.log ;;
esac
case ${1:-} in
  r7test) for e in "GGML_HIP_MMVQ_Q6FR=1" "GGML_HIP_GDN_FUSED=1"; do echo "== $e"
            for o in MUL_MAT GATED_DELTA_NET FLASH_ATTN_EXT_MASKED_TAIL; do env $e LD_LIBRARY_PATH=$NEW:$R timeout 280 $NEW/test-backend-ops test -o $o 2>&1 | grep -E "FAIL|passed|Backend ROCm0" | tail -2 | tr '\n' ' '; echo " ($o)"; done; done
          for q in 0 1; do echo "== perf Q6FR=$q"; env GGML_HIP_MMVQ_Q6FR=$q LD_LIBRARY_PATH=$NEW:$R timeout 280 $NEW/test-backend-ops perf -o MUL_MAT 2>&1 | grep -E "type_a=q6_K,type_b=f32,m=(248320|5120),n=(1|2),k=(5120|17408)" | sed -E 's/ +/ /g; s/,bs=.*://' ; done ;;
  r7bench) for b in OLD NEW OLD NEW; do B=${!b}
          echo "$b $(LD_LIBRARY_PATH=$B:$R $B/llama-bench -m $M -p 512,2048 -n 0 -fa on -ngl 99 -ctk q4_0 -ctv q4_0 -ub 2048 -r 3 2>&1 | grep -E 'pp[0-9]' | awk -F'|' '{printf "%s %s; ", $(NF-2), $(NF-1)}')"; done
        for a in "0 0 0" "1 0 0" "0 1 0" "0 0 1" "1 1 1" "0 0 0" "1 0 0" "0 1 0" "0 0 1" "1 1 1"; do set -- $a
          echo "Q6FR=$1 GDNF=$2 TURBO=$3 $(env GGML_HIP_MMVQ_Q6FR=$1 GGML_HIP_GDN_FUSED=$2 GGML_HIP_MMVQ_TURBO=$3 GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0 LD_LIBRARY_PATH=$NEW:$R $NEW/llama-bench -m $M -p 0 -n 64 -fa on -ngl 99 -ctk q4_0 -ctv q4_0 -r 3 2>&1 | grep -E 'tg[0-9]' | awk -F'|' '{printf "%s %s; ", $(NF-2), $(NF-1)}')"; done ;;
  r7kld) cd ~/qwen-opt/duo; T=~/wt/lfm3-prof/wikitext-2-raw/wiki.test.raw
       for ub in 1 5; do
         env GGML_HIP_MMVQ_Q6FR=1 GGML_HIP_GDN_FUSED=1 LD_LIBRARY_PATH=$NEW:$R GGML_HIP_PM4=0 $NEW/llama-perplexity -m $M -f $T -c 8192 --chunks 2 -b 8192 -ngl 999 -fa on -ub $ub -ctk q4_0 -ctv q4_0 --kl-divergence-base ref.kld --kl-divergence > r7on$ub.log 2>&1
         echo "== ub $ub Q6FR+GDN_FUSED vs off"; python3 ~/qwen-opt/tools/kld_gate.py compare r4off$ub.log r7on$ub.log
       done ;;
esac
case ${1:-} in
  r8test) env GGML_HIP_MMVQ_V5=1 LD_LIBRARY_PATH=$NEW:$R timeout 400 $NEW/test-backend-ops test -o MUL_MAT 2>&1 | grep -E "FAIL|passed|Backend ROCm0" | tail -3
          for v in 0 1 0 1; do echo "== perf V5=$v"; env GGML_HIP_MMVQ_V5=$v LD_LIBRARY_PATH=$NEW:$R timeout 280 $NEW/test-backend-ops perf -o MUL_MAT -p "type_a=q[46]_K,type_b=f32,m=(5120|6144|17408|248320),n=5,k=(5120|17408)" 2>&1 | grep -E "us/run" | sed -E 's/ +/ /g; s/,bs=[^:]*:/:/; s/MUL_MAT\(type_a=//; s/ - [0-9.]+ [GMT]FLOP.*//' ; done ;;
  r8bench) for v in 0 1 0 1; do
          echo "V5=$v $(env GGML_HIP_MMVQ_V5=$v GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0 LD_LIBRARY_PATH=$NEW:$R $NEW/llama-bench -m $M -p 5 -ub 5 -n 0 -fa on -ngl 99 -ctk q4_0 -ctv q4_0 -d 0,8192 -r 10 2>&1 | grep -E 'pp5' | awk -F'|' '{printf "%s %s; ", $(NF-2), $(NF-1)}')"; done ;;
  r8kld) cd ~/qwen-opt/duo; T=~/wt/lfm3-prof/wikitext-2-raw/wiki.test.raw
       env GGML_HIP_MMVQ_V5=1 LD_LIBRARY_PATH=$NEW:$R GGML_HIP_PM4=0 $NEW/llama-perplexity -m $M -f $T -c 8192 --chunks 2 -b 8192 -ngl 999 -fa on -ub 5 -ctk q4_0 -ctv q4_0 --kl-divergence-base ref.kld --kl-divergence > r8on5.log 2>&1
       echo "== ub 5 V5 vs off"; python3 ~/qwen-opt/tools/kld_gate.py compare r4off5.log r8on5.log ;;
esac
case ${1:-} in
  r8fail) env GGML_HIP_MMVQ_V5=1 LD_LIBRARY_PATH=$NEW:$R timeout 400 $NEW/test-backend-ops test -o MUL_MAT 2>&1 | grep -E "FAIL" | head -12 ;;
esac
case ${1:-} in
  r9test) for v in 0 2 3 1; do echo "== V5=$v $(env GGML_HIP_MMVQ_V5=$v LD_LIBRARY_PATH=$NEW:$R timeout 200 $NEW/test-backend-ops test -o MUL_MAT -p 'type_a=(q4_K|q6_K),n=5' 2>&1 | grep -E 'FAIL|passed' | tr '\n' ' ')"; done
          env GGML_HIP_MMVQ_V5=1 LD_LIBRARY_PATH=$NEW:$R timeout 400 $NEW/test-backend-ops test -o MUL_MAT 2>&1 | grep -E "FAIL" | head -8 ;;
  r9bench) for v in 0 1 0 1; do
          echo "V5=$v $(env GGML_HIP_MMVQ_V5=$v GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0 LD_LIBRARY_PATH=$NEW:$R $NEW/llama-bench -m $M -p 5 -ub 5 -n 0 -fa on -ngl 99 -ctk q4_0 -ctv q4_0 -d 0,8192 -r 10 2>&1 | grep -E 'pp5' | awk -F'|' '{printf "%s %s; ", $(NF-2), $(NF-1)}')"; done ;;
esac
case ${1:-} in
  r10test) for o in FLASH_ATTN_EXT FLASH_ATTN_EXT_MASKED_TAIL; do echo "== $o $(env GGML_HIP_FA_NATIVE_Q4=1 LD_LIBRARY_PATH=$NEW:$R timeout 300 $NEW/test-backend-ops test -o $o 2>&1 | grep -E 'FAIL|passed' | tail -2 | tr '\n' ' ')"; done ;;
  r10bench) for v in 0 1 0 1; do
          echo "NQ4=$v $(env GGML_HIP_FA_NATIVE_Q4=$v GGML_HIP_FA_D256_VAR=83 LD_LIBRARY_PATH=$NEW:$R $NEW/llama-bench -m $M -p 2048 -n 0 -fa on -ngl 99 -ctk q4_0 -ctv q4_0 -ub 2048 -d 0,32768 -r 3 2>&1 | grep -E 'pp2048' | awk -F'|' '{printf "%s %s; ", $(NF-2), $(NF-1)}')"; done ;;
  r10kld) cd ~/qwen-opt/duo; T=~/wt/lfm3-prof/wikitext-2-raw/wiki.test.raw
       env GGML_HIP_FA_NATIVE_Q4=1 GGML_HIP_FA_D256_VAR=83 LD_LIBRARY_PATH=$NEW:$R GGML_HIP_PM4=0 $NEW/llama-perplexity -m $M -f $T -c 8192 --chunks 2 -b 8192 -ngl 999 -fa on -ub 512 -ctk q4_0 -ctv q4_0 --kl-divergence-base ref.kld --kl-divergence > r10on512.log 2>&1
       echo "== ub 512 NATIVE_Q4 vs fix"; python3 ~/qwen-opt/tools/kld_gate.py compare fix512.log r10on512.log ;;
esac
