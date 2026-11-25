#!/usr/bin/env bash
# Drafter gate for Bonsai 2.5 Uncensored on topka-k157 (drafter-plan.md, 2026-11-25), no build needed:
#   real arms:      draft acceptance per request at T=0 and T=0.7 (wall.py: code, tech, pl, json)
#   synthetic arms: server round cost at a given acceptance curve (--spec-synth-rates), i.e. the t/s a drafter with
#                   that curve would reach on this engine; text is not valid model output there
# usage: drafter-gate.sh TAG SPEC N [extra server args...]
#   SPEC   mtp | dflash (Qwen3.8-27B-DFlash2-Q4_K_M; cost only: topka's DFlash graph does not apply the Hadamard
#          inverse to the borrowed token_embd, so its real acceptance on Bonsai is not meaningful)
#   SYNTH  c1,c2,... cumulative acceptance curve (P(first i drafts accepted)), cut to N; empty = real verification
#   LOOKUP production 3 (default); use 0 on synthetic arms. PM4 1 (default) | 0.
#   WALL_TOPK / WALL_TOPP default 20 / 0.95 = the GGUF's general.sampling defaults, sent explicitly (min_p stays at the
#   GGUF default 0.05: wall.py does not send it); WALL_TOPK=0 WALL_TOPP=1.0 for the untruncated (min_p 0.05) arm.
# port 18796 (never 8080), taskset -c 2-5, the exit trap kills by port.
set -uo pipefail
tag=$1 sp=$2 n=$3; shift 3
B=$HOME/wt/topka-k157/build-hip/bin
M=$HOME/models/bonsai25/Ternary-Bonsai-2.5-27B-Uncensored-Q2_0-mtp.gguf
DF=$HOME/models/draft/Qwen3.8-27B-DFlash2-Q4_K_M.gguf
DV=$HOME/models/draft/draft_vocab_qwen38.txt
PORT=18796; out=$HOME/qwen-opt/bonsai25/out; mkdir -p "$out"; log=$out/dg-$tag.server.log
case $sp in
  mtp)    spec=(--spec-type draft-mtp --spec-draft-n-max "$n" -ctkd q4_0 -ctvd q4_0 --spec-draft-vocab "$DV" --spec-draft-vocab-n 65536);;
  dflash) spec=(-md "$DF" -ngld 99 --spec-type draft-dflash --spec-draft-n-max "$n" -ctkd q4_0 -ctvd q4_0);;
  *) echo "SPEC must be mtp|dflash"; exit 2;;
esac
if [ -n "${SYNTH:-}" ]; then
  spec+=(--spec-synth-rates "$(echo "$SYNTH" | cut -d, -f1-"$n")" --spec-draft-p-min 0)
fi
export LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib
if [ "${PM4:-1}" = 1 ]; then
  export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0 GGML_HIP_PM4_MIN_DISPATCH=16 GGML_HIP_PM4_LAZY_EXEC=1
else
  export GGML_HIP_PM4=0
fi
export GGML_HIP_FA_D256_VAR=83 LLAMA_SPEC_LOOKUP=${LOOKUP:-3} LLAMA_SPEC_LOOKUP_W=16 LLAMA_GPU_VERIFY=1 LLAMA_SPEC_COUPLED=1 \
  LLAMA_SERVER_YIELD_FAST=2 LLAMA_SERVER_CACHE_SHARE_MIN=1024
export WALL_TOPK=${WALL_TOPK-20} WALL_TOPP=${WALL_TOPP-0.95}

killport() {
  pkill -TERM -f -- "--port $PORT" 2>/dev/null
  for _ in $(seq 45); do pgrep -f -- "--port $PORT" >/dev/null || return 0; sleep 1; done
  pkill -KILL -f -- "--port $PORT" 2>/dev/null
}
~/qwen-opt/l1tok/chat8080.sh stop
killport
taskset -c 2-5 "$B/llama-server" -m "$M" -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c 262144 -np 1 --jinja --no-webui \
    --host 127.0.0.1 --port $PORT "${spec[@]}" "$@" > "$log" 2>&1 &
srv=$!
trap 'kill -TERM $srv 2>/dev/null; killport' EXIT
for _ in $(seq 300); do
  curl -sf "127.0.0.1:$PORT/health" >/dev/null && break
  kill -0 $srv 2>/dev/null || { echo "dg-$tag: server exited"; tail -12 "$log"; exit 1; }
  sleep 1
done
echo "dg-$tag: SPEC=$sp N=$n SYNTH=${SYNTH:-} LOOKUP=${LOOKUP:-3} PM4=${PM4:-1} TOPK=${WALL_TOPK:-none} TOPP=${WALL_TOPP:-none}" | tee -a "$out/drafter-gate.txt"
taskset -c 2-5 timeout 600 python3 ~/qwen-opt/nib/wall.py $PORT "dg-$tag" | tee -a "$out/drafter-gate.txt"
echo "dg-$tag: draft acceptance per request (order: T=0 code tech pl json, T=0.7 code tech pl json)" | tee -a "$out/drafter-gate.txt"
grep -E "draft acceptance" "$log" | sed -E 's/.*(draft acceptance.*)/\1/' | tee -a "$out/drafter-gate.txt"
journalctl -k --since "-15min" --no-pager | grep -c gfxhub
