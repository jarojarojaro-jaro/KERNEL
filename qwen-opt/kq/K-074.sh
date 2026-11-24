#!/usr/bin/env bash
# K-074 (Orca part): OrcaCyber-Nano-1.0 on XTX, built-in MTP vs DFlash2 drafter (until now only on the 3090), xbench Q1-Q6, L2048, L8192.
# Production fork ~/llama-opt (same as run-llm.sh rocm), KV q4_0, ctx 32768, test port 18796 (never 8080), taskset -c 2-5.
# PM4 rule: GGML_HIP_PM4=0 (non-production model). usage: K-074.sh mtp|dflash|none [N]
set -uo pipefail
mode=$1; n=${2:-}
export GGML_HIP_PM4=0 LD_LIBRARY_PATH=$HOME/llama-opt/lib:/opt/rocm/core-10.0/lib
M=$HOME/models/orca-cyber-nano; PORT=18796
out=$(cd "$(dirname "$0")" && pwd)/out; mkdir -p "$out"
case $mode in
    mtp)    spec=(--spec-type draft-mtp --spec-draft-n-max "${n:-4}" -ctkd q4_0 -ctvd q4_0) ;;
    dflash) spec=(-md "$M/OrcaCyber-Nano-1.0-AI-Defense-DFlash2-Q8_0.gguf" -ngld 99 --spec-type draft-dflash --spec-draft-n-max "${n:-6}") ;;
    none)   spec=() ;;
    *) echo "mode mtp|dflash|none" >&2; exit 2 ;;
esac
tag=orca-$mode${n}
~/qwen-opt/l1tok/chat8080.sh stop
taskset -c 2-5 "$HOME/llama-opt/bin/llama-server" -m "$M/OrcaCyber-Nano-1.0-AI-Defense-Mix-15.7G.gguf" -ngl 999 -fa on \
    -ctk q4_0 -ctv q4_0 -c 32768 -np 1 --jinja --no-webui --host 127.0.0.1 --port $PORT "${spec[@]}" > "$out/K-074-$tag.server.log" 2>&1 &
srv=$!
trap 'kill -TERM $srv 2>/dev/null; for _ in $(seq 45); do kill -0 $srv 2>/dev/null || break; sleep 1; done; kill -9 $srv 2>/dev/null' EXIT
for _ in $(seq 300); do
    curl -sf "127.0.0.1:$PORT/health" >/dev/null && break
    kill -0 $srv 2>/dev/null || { echo "$tag: server exited"; tail -8 "$out/K-074-$tag.server.log"; exit 1; }
    sleep 1
done
taskset -c 2-5 timeout 600 python3 ~/turbo-jobs/xbench.py $PORT ~/turbo/tests "$tag" | tee -a "$out/K-074.txt"
grep -E "draft acceptance|accept" "$out/K-074-$tag.server.log" | tail -2
