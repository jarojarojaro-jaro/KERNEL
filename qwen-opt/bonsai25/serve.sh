#!/usr/bin/env bash
# Ternary Bonsai 2.5 27B Uncensored (AtomicChat) on XTX, best measured 2026-11-25: our topka fork, branch topka-best
# (~/wt/topka-best: Hadamard port c76335b + K-150T fusions + K-154 Q2_0 WMMA 9..16 + K-155 MMVF split), Q2_0 lossless repack
# + prism MTP head, PM4 replay, production env (lookup W16, coupled, GPU verify), MTP n2, draft vocab 64k, KV q4_0, ctx 262144:
# chat T=0.7 106.5-112, plain 70.6, code edit/copy 426 t/s, prefill 2k/8k 784/854. Port 18796 (never 8080); holds /tmp/gpu.lock while serving (stops :8080,
# restores it on exit). Stop: touch ~/qwen-opt/bonsai25/STOP
exec 8>>/tmp/gpu.lock; flock 8
rm -f ~/qwen-opt/bonsai25/STOP
B=$HOME/wt/topka-best/build-hip/bin; export LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib
export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0 GGML_HIP_FA_D256_VAR=83 LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 \
  LLAMA_GPU_VERIFY=1 LLAMA_SPEC_COUPLED=1 LLAMA_SERVER_YIELD_FAST=2 GGML_HIP_PM4_MIN_DISPATCH=16 GGML_HIP_PM4_LAZY_EXEC=1 LLAMA_SERVER_CACHE_SHARE_MIN=1024
restore() { kill -TERM $SPID 2>/dev/null; sleep 5; kill -KILL $SPID 2>/dev/null; kill $GPID 2>/dev/null; ~/qwen-opt/l1tok/chat8080.sh restore 8>&-; }
trap restore EXIT
~/qwen-opt/l1tok/chat8080.sh stop 8>&-
~/qwen-opt/tools/gpu-guard.sh > ~/qwen-opt/bonsai25/gpu-guard.out 2>&1 8>&- & GPID=$!
taskset -c 2-5 $B/llama-server -m $HOME/models/bonsai25/Ternary-Bonsai-2.5-27B-Uncensored-Q2_0-mtp.gguf -ngl 999 -fa on \
  -ctk q4_0 -ctv q4_0 -c ${CTX:-262144} -np 1 --jinja --host 0.0.0.0 --port 18796 \
  --spec-type draft-mtp --spec-draft-n-max 2 -ctkd q4_0 -ctvd q4_0 \
  --spec-draft-vocab $HOME/models/draft/draft_vocab_qwen38.txt --spec-draft-vocab-n 65536 --temp 0.7 --min-p 0 \
  > ~/qwen-opt/bonsai25/serve.log 2>&1 8>&- & SPID=$!
for i in $(seq 4320); do [ -f ~/qwen-opt/bonsai25/STOP ] && break; kill -0 $SPID 2>/dev/null || break; sleep 10; done
