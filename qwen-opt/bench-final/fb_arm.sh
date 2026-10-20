#!/usr/bin/env bash
# One server arm of the final XTX before/after table (WYNIKI-XTX-2026-10-19): a fresh llama-server, VRAM + ctx after
# load, then the benchmarks, then the server is stopped. Run ONLY from ~/qwen-opt/queue/run-jobs.sh (it holds the GPU
# and quiet locks and has stopped topka); this script never starts topka on 8080.
#   fb_arm.sh MODEL ARM PASS BENCHES
#   MODEL   qwen | uncensored | lfm | lfm-uncensored                 (the run-llm.sh model keys)
#   ARM     U0 = upstream ~/llama-upstream, defaults: only -m (fit picks ctx, f16 KV, no speculation)
#           U1 = upstream with the production flags of run-llm.sh (ctx, KV, -fa on, -np 1, effort low) + for Qwen its
#                own MTP (--spec-type draft-mtp --spec-draft-n-max 4, draft KV like main; = A1 of cloud/bench.sh)
#           T  = topka exactly as the user runs it: ~/qwen-opt/run-topka.sh MODEL with the PM4 WA=2 env
#   PASS    1 | 2 (label suffix; the jobs file orders the arms A/B/B/A across passes)
#   BENCHES comma list of: sweep (spec_sweep 6 prompts x seeds 1,2,3, T=1, 400 tok), mvs (copy_bench --set mvs T=0,
#           1024 tok), copy (copy_bench --set short T=0, 512 tok), long (fb_long.py, frozen ~32k prompt)
# Logs: ~/qwen-opt/bench-final/logs/<model>.<arm>.p<pass>.server.log, spec_sweep.jsonl, copy_bench.jsonl, long.jsonl,
#       vram.jsonl
set -euo pipefail
model=$1; arm=$2; pass=$3; benches=$4
FB=$HOME/qwen-opt/bench-final; LOGDIR=$FB/logs; mkdir -p "$LOGDIR"
label=$model.$arm.p$pass
slog=$LOGDIR/$label.server.log
py=$HOME/qwen-opt/.venv/bin/python
UP=$HOME/llama-upstream/bin
case $model in
    qwen)           gguf=$HOME/models/Qwen3.8-27B-UD-Q4_K_XL.gguf;                 kv=q4_0; ctx=204800 ;;
    uncensored)     gguf=$HOME/models/orca/Qwen3.8-27B-Uncensored-Q4_K_M.gguf;      kv=q4_0; ctx=204800 ;;
    lfm)            gguf=$HOME/models/lfm/LFM2.5-24B-A2B-Q5_K_M.gguf;               kv=q8_0; ctx=131072 ;;
    lfm-uncensored) gguf=$HOME/models/lfm/LFM2.5-24B-A2B-Uncensored-AD-Q5_K_M.gguf; kv=q8_0; ctx=131072 ;;
    *) echo "unknown model $model" >&2; exit 2 ;;
esac
case $arm in U0) port=18701 ;; U1) port=18702 ;; T) port=18703 ;; *) echo "unknown arm $arm" >&2; exit 2 ;; esac

pkill -f 'llama-topka/bin/llama-server.*--port 8080' && sleep 5 || true
"$HOME/qwen-opt/lookup/vram_ok.sh"
vram_used() { amd-smi metric -m 2>/dev/null | awk '/ USED_VRAM:/ {print $2; exit}'; }
vram0=$(vram_used)

latest=$(readlink "$HOME/qwen-opt/logs/latest.log" 2>/dev/null || true)
pg=
cleanup() {
    [ -n "$pg" ] && kill -- "-$pg" 2>/dev/null || true
    for _ in $(seq 30); do pgrep -f "llama-server.*--port $port" > /dev/null || break; sleep 1; done
    pkill -9 -f "llama-server.*--port $port" 2>/dev/null || true
    # run-llm.sh repoints logs/latest.log at our log; give it back to the live topka log
    [ -n "$latest" ] && ln -sfn "$latest" "$HOME/qwen-opt/logs/latest.log" || true
}
trap cleanup EXIT
trap 'exit 1' TERM INT

start() {  # start the arm's server in its own process group (setsid), pinned to cores 2-5
    case $arm in
        U0) setsid env LD_LIBRARY_PATH="$UP:/opt/rocm/core-10.0/lib" GGML_HIP_PM4=0 taskset -c 2-5 "$UP/llama-server" \
                -m "$gguf" --host 127.0.0.1 --port "$port" --no-webui > "$slog" 2>&1 & ;;
        U1) local spec=() think=()
            case $model in qwen|uncensored)
                spec=(--spec-type draft-mtp --spec-draft-n-max 4 -ctkd "$kv" -ctvd "$kv"); think=(--reasoning-effort low) ;;
            esac
            setsid env LD_LIBRARY_PATH="$UP:/opt/rocm/core-10.0/lib" GGML_HIP_PM4=0 taskset -c 2-5 "$UP/llama-server" \
                -m "$gguf" -ngl 999 -fa on -ctk "$kv" -ctv "$kv" -c "$1" -np 1 --jinja --cache-ram 16384 "${think[@]}" \
                --host 127.0.0.1 --port "$port" --no-webui "${spec[@]}" > "$slog" 2>&1 & ;;
        T)  setsid env GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0 LLAMA_GPU_VERIFY=1 \
                PORT="$port" LOG="$slog" taskset -c 2-5 "$HOME/qwen-opt/run-topka.sh" "$model" > "$slog.stdout" 2>&1 & ;;
    esac
    pg=$!
    for _ in $(seq 300); do
        curl -sf "http://127.0.0.1:$port/health" > /dev/null && return 0
        kill -0 "$pg" 2>/dev/null || return 1
        sleep 1
    done
    return 1
}

used_ctx=$ctx
if [ "$arm" = U1 ]; then
    # upstream may not fit the production ctx (full-vocab MTP head, no IQ4_XS head): step down, logged
    for c in $ctx 131072 65536; do
        used_ctx=$c
        start "$c" && break
        echo "$label: upstream did not start at ctx $c"; tail -3 "$slog"; cleanup; pg=
        [ "$c" = 65536 ] && exit 1
    done
else
    start || { echo "$label: server failed"; tail -20 "$slog" "$slog.stdout" 2>/dev/null; exit 1; }
fi
sleep 3
vram1=$(vram_used)
nctx=$(curl -sf "http://127.0.0.1:$port/props" | "$py" -c 'import json,sys; d=json.load(sys.stdin); print(d.get("default_generation_settings",{}).get("n_ctx") or d.get("n_ctx"))' 2>/dev/null || echo "?")
echo "{\"label\":\"$label\",\"vram_before_mb\":${vram0:-null},\"vram_loaded_mb\":${vram1:-null},\"n_ctx\":\"$nctx\",\"ctx_requested\":\"$( [ "$arm" = U0 ] && echo default || echo "$used_ctx")\"}" \
    | tee -a "$LOGDIR/vram.jsonl"

for b in ${benches//,/ }; do
    case $b in
        sweep) (cd "$LOGDIR" && taskset -c 2-5 "$py" "$HOME/qwen-opt/spec_sweep.py" --label "$label" --port "$port" \
                    --temps 1.0 --seeds 1,2,3 --tokens 400) ;;
        mvs)   taskset -c 2-5 "$py" "$HOME/qwen-opt/lookup/copy_bench.py" --label "$label" --port "$port" --set mvs \
                    --temps 0.0 --tokens 1024 --out "$LOGDIR/copy_bench.jsonl" ;;
        copy)  taskset -c 2-5 "$py" "$HOME/qwen-opt/lookup/copy_bench.py" --label "$label" --port "$port" --set short \
                    --temps 0.0 --tokens 512 --out "$LOGDIR/copy_bench.jsonl" ;;
        long)  taskset -c 2-5 "$py" "$FB/fb_long.py" --label "$label" --port "$port" --out "$LOGDIR/long.jsonl" ;;
        *) echo "unknown bench $b" >&2; exit 2 ;;
    esac
done
grep -h -E "context lookup|draft acceptance rate" "$slog" 2>/dev/null | tail -2 || true
