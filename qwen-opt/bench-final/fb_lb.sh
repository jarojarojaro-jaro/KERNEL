#!/usr/bin/env bash
# llama-bench part of the final XTX before/after table, rounds in the given order (default "U T T U", A/B/B/A).
# Run ONLY from ~/qwen-opt/queue/run-jobs.sh (GPU + quiet locks held, topka stopped).
#   fb_lb.sh MODEL [ORDER]
#   U = upstream ~/llama-upstream: -fa 1 -p 512,4096 -n 128 -r 3 -ngl 999, KV as run-llm.sh (q4_0 Qwen, q8_0 LFM)
#   T = topka ~/llama-topka: the same + the run-topka.sh environment (PM4 WA=2 + GUARD, HSA_USE_SVM=0) and, for LFM,
#       its -b 2048 -ub 2048
# Output: ~/qwen-opt/bench-final/logs/lb.<model>.<U|T>.r<i>.jsonl (llama-bench -o jsonl)
set -euo pipefail
model=$1; order=${2:-U T T U}
LOGDIR=$HOME/qwen-opt/bench-final/logs; mkdir -p "$LOGDIR"
case $model in
    qwen)           gguf=$HOME/models/Qwen3.8-27B-UD-Q4_K_XL.gguf;                 kv=q4_0; tub=() ;;
    uncensored)     gguf=$HOME/models/orca/Qwen3.8-27B-Uncensored-Q4_K_M.gguf;      kv=q4_0; tub=() ;;
    lfm)            gguf=$HOME/models/lfm/LFM2.5-24B-A2B-Q5_K_M.gguf;               kv=q8_0; tub=(-b 2048 -ub 2048) ;;
    lfm-uncensored) gguf=$HOME/models/lfm/LFM2.5-24B-A2B-Uncensored-AD-Q5_K_M.gguf; kv=q8_0; tub=(-b 2048 -ub 2048) ;;
    *) echo "unknown model $model" >&2; exit 2 ;;
esac
pkill -f 'llama-topka/bin/llama-server.*--port 8080' && sleep 5 || true
"$HOME/qwen-opt/lookup/vram_ok.sh"
trap 'pkill -f "llama-(upstream|topka)/bin/llama-bench" 2>/dev/null || true' EXIT
trap 'exit 1' TERM INT
common=(-m "$gguf" -ngl 999 -fa 1 -ctk "$kv" -ctv "$kv" -p 512,4096 -n 128 -r 3 -o jsonl)
i=0
for a in $order; do
    i=$((i + 1)); out=$LOGDIR/lb.$model.$a.r$i.jsonl
    case $a in
        U) env LD_LIBRARY_PATH="$HOME/llama-upstream/bin:/opt/rocm/core-10.0/lib" GGML_HIP_PM4=0 \
               taskset -c 2-5 "$HOME/llama-upstream/bin/llama-bench" "${common[@]}" > "$out" ;;
        T) env LD_LIBRARY_PATH="$HOME/llama-topka/lib:/opt/rocm/core-10.0/lib" GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 \
               GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0 LLAMA_GPU_VERIFY=1 \
               taskset -c 2-5 "$HOME/llama-topka/bin/llama-bench" "${common[@]}" "${tub[@]}" > "$out" ;;
        *) echo "unknown arm $a" >&2; exit 2 ;;
    esac
    echo "$model $a r$i: $(jq -r '"\(.n_prompt)/\(.n_gen) \((.avg_ts * 10 | round) / 10)"' "$out" | tr '\n' ' ')"
done
