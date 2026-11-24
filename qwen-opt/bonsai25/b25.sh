#!/usr/bin/env bash
# Ternary Bonsai 2.5 27B Uncensored (AtomicChat) on XTX: xbench Q1-Q6 (Q6 T=0.7), L2048, L8192.
# usage: b25.sh ENGINE MODEL SPEC [N] [extra server args...]
#   ENGINE prism (PrismML fork 910442b, HIP gfx1100) | up (upstream-master 6792507b7) | other dir with bin/llama-server
#   MODEL  ptq1 | q2  (…-Uncensored-{PTQ1_0,Q2_0}-mtp.gguf, lossless repack, MTP head from prism)
#   SPEC   mtp | none
# KV q4_0 (MTP draft too), ctx 32768, port 18796 (never 8080), taskset -c 2-5, GGML_HIP_PM4=0 (non-production engine).
set -uo pipefail
eng=$1 mod=$2 sp=$3 n=${4:-3}; shift 4 2>/dev/null || shift $#
case $eng in prism) B=$HOME/wt/prism/build-hip/bin;; up) B=$HOME/wt/upstream-master/build-hip/bin;; *) B=$eng;; esac
case $mod in ptq1) M=$HOME/models/bonsai25/Ternary-Bonsai-2.5-27B-Uncensored-PTQ1_0-mtp.gguf;; q2) M=$HOME/models/bonsai25/Ternary-Bonsai-2.5-27B-Uncensored-Q2_0-mtp.gguf;; esac
case $sp in mtp) spec=(--spec-type draft-mtp --spec-draft-n-max "$n" -ctkd q4_0 -ctvd q4_0);; none) spec=();; esac
export GGML_HIP_PM4=0 LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib
PORT=18796; out=$HOME/qwen-opt/bonsai25/out; mkdir -p "$out"
tag=b25-$(basename "$eng")-$mod-$sp$([ $sp = mtp ] && echo $n)${EXTRA_TAG:-}
~/qwen-opt/l1tok/chat8080.sh stop
taskset -c 2-5 "$B/llama-server" -m "$M" -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c 32768 -np 1 --jinja --no-webui \
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
grep -E "draft acceptance" "$out/$tag.server.log" | tail -2
journalctl -k --since "-15min" --no-pager | grep -c gfxhub
