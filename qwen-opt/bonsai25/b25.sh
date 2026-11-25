#!/usr/bin/env bash
# Ternary Bonsai 2.5 27B Uncensored (AtomicChat) on XTX: xbench Q1-Q6 (Q6 T=0.7), L2048, L8192.
# usage: b25.sh ENGINE MODEL SPEC [N] [extra server args...]
#   ENGINE prism (PrismML fork 910442b, HIP gfx1100) | up (upstream-master 6792507b7) | other dir with bin/llama-server
#   MODEL  ptq1 | q2  (…-Uncensored-{PTQ1_0,Q2_0}-mtp.gguf, lossless repack, MTP head from prism)
#   SPEC   mtp | dflash (Qwen3.8-27B-DFlash2-Q4_K_M drafter) | none
# context: CTX (default 262144 = full, JARO 2026-11-25)
# KV q4_0 (MTP draft too), ctx 32768, port 18796 (never 8080), taskset -c 2-5, GGML_HIP_PM4=0 (non-production engine).
set -uo pipefail
eng=$1 mod=$2 sp=$3 n=${4:-3}; shift 4 2>/dev/null || shift $#
case $eng in prism) B=$HOME/wt/prism/build-hip/bin;; topka) B=$HOME/wt/topka-bonsai/build-hip/bin;; k150) B=$HOME/wt/prism-k150/build-hip/bin;; pt) B=$HOME/wt/prism-pt/build-hip/bin;; k150t) B=$HOME/wt/topka-k150t/build-hip/bin;; bz16) B=$HOME/wt/topka-bz16/build-hip/bin;; best) B=$HOME/wt/topka-best/build-hip/bin;; up) B=$HOME/wt/upstream-master/build-hip/bin;; *) B=$eng;; esac
case $mod in ptq1) M=$HOME/models/bonsai25/Ternary-Bonsai-2.5-27B-Uncensored-PTQ1_0-mtp.gguf;; q2) M=$HOME/models/bonsai25/Ternary-Bonsai-2.5-27B-Uncensored-Q2_0-mtp.gguf;; esac
DF=$HOME/models/draft/Qwen3.8-27B-DFlash2-Q4_K_M.gguf
case $sp in mtp) spec=(--spec-type draft-mtp --spec-draft-n-max "$n" -ctkd q4_0 -ctvd q4_0);; dflash) spec=(-md "$DF" -ngld 99 --spec-type draft-dflash --spec-draft-n-max "$n" -ctkd q4_0 -ctvd q4_0);; none) spec=();; esac
export LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib
if [ "${PM4:-0}" = 1 ]; then export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0; else export GGML_HIP_PM4=0; fi
if [ "${PROD:-0}" = 1 ]; then  # production topka env (run-topka.sh), Bonsai only differs in model
  export GGML_HIP_FA_D256_VAR=83 LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=${LOOKUP_W:-16} LLAMA_GPU_VERIFY=1 LLAMA_SPEC_COUPLED=1 \
    LLAMA_SERVER_YIELD_FAST=2 GGML_HIP_PM4_MIN_DISPATCH=16 GGML_HIP_PM4_LAZY_EXEC=1 LLAMA_SERVER_CACHE_SHARE_MIN=1024
fi
PORT=18796; out=$HOME/qwen-opt/bonsai25/out; mkdir -p "$out"
tag=b25-$(basename "$eng")$([ "${PM4:-0}" = 1 ] && echo -pm4)$([ "${PROD:-0}" = 1 ] && echo -prod)-$mod-$sp$([ $sp != none ] && echo $n)-c${CTX:-262144}${EXTRA_TAG:-}
~/qwen-opt/l1tok/chat8080.sh stop
taskset -c 2-5 "$B/llama-server" -m "$M" -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c ${CTX:-262144} -np 1 --jinja --no-webui \
    --host 127.0.0.1 --port $PORT "${spec[@]}" "$@" > "$out/$tag.server.log" 2>&1 &
srv=$!
trap 'kill -TERM $srv 2>/dev/null; for _ in $(seq 45); do kill -0 $srv 2>/dev/null || break; sleep 1; done; kill -9 $srv 2>/dev/null' EXIT
for _ in $(seq 300); do
    curl -sf "127.0.0.1:$PORT/health" >/dev/null && break
    kill -0 $srv 2>/dev/null || { echo "$tag: server exited"; tail -12 "$out/$tag.server.log"; exit 1; }
    sleep 1
done
grep -m3 -iE "hadamard|PTQ1|Q2_0|model size|CUDA0 model buffer|ROCm0 model buffer" "$out/$tag.server.log"
taskset -c 2-5 timeout 600 python3 ~/turbo-jobs/xbench.py $PORT ~/turbo/tests "$tag" | tee -a "$out/b25.txt"
if [ -n "${BENCH_COPY:-}" ]; then
  taskset -c 2-5 timeout 500 python3 ~/qwen-opt/lookup/copy_bench.py --label "$tag" --port $PORT --set short --temps 0.0,0.7 --seeds 1 --tokens 512 \
    --out "$out/copy.jsonl" 2>&1 | tail -8
fi
grep -E "draft acceptance" "$out/$tag.server.log" | tail -2
journalctl -k --since "-15min" --no-pager | grep -c gfxhub
