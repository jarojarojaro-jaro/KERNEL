# ON the 4070 Ti box, sourced: server arms for Qwen3.8-27B UD-IQ3_XXS (user directive 2026-10-20: KV q4_0, max ctx).
#   U0  upstream `llama-server -m X` (defaults: -fit, KV f16, no speculation)
#   U1  upstream + production flags (-fit off -ngl 99, FA, KV q4_0 incl. draft, ctx $CTX, -np 1, MTP n=$NMAX)
#   T   our tree ($TK, default nv build) + U1 flags + 64k draft vocab, iq4_xs heads, lookup W16, cache share, GPU verify
# Extra env for T (A/B switches) comes from $TENV (e.g. TENV="GGML_CUDA_X=1"). Benchmarks pinned to the GPU's NUMA
# node 1 physical cores 6-11 (nvidia-smi topo: CPU affinity 6-11,18-23).
H=/root/cloud; M=/root/models; S=/root/src
RES=/root/results/opt-4070ti-20261020; L=$RES/logs; G=$RES/gate
mkdir -p "$L" "$G"
UP=${UP:-$S/upstream/b89/bin}; TK=${TK:-$S/nv/b89/bin}
GGUF=${GGUF:-$M/Qwen3.8-27B-UD-Q2_K_XL.gguf}   # decision 2026-10-20: IQ3_XXS does not fit T at 32k (probe logs)
CTX=${CTX:-36864}; NMAX=${NMAX:-4}; TV=${TV:-1}; TENV=${TENV:-}; PFX=${PFX:-}   # PFX: command prefix (nsys profile ...)
UB=${UB:-512}   # -ub: the compute buffers of both contexts scale with it (logits rows of the reserve graph)
PORT=18741
BC="taskset -c 6-11"
vram() { nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1; }
say() { echo "=== $(date +%T) $*"; }
pid=
srv_stop() {
    [ -n "$pid" ] || return 0
    kill "$pid" 2>/dev/null
    for _ in $(seq 30); do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
    kill -9 "$pid" 2>/dev/null; wait "$pid" 2>/dev/null; pid=
    sleep 3
}
trap srv_stop EXIT
srv() {  # arm log
    local common=(-m "$GGUF" -fit off -ngl 99 -t 6 -fa on -ctk q4_0 -ctv q4_0 -c "$CTX" -ub "$UB" -np 1 --jinja --cache-ram 8192
                  --reasoning-effort low --host 127.0.0.1 --port $PORT --no-webui
                  --spec-type draft-mtp --spec-draft-n-max "$NMAX" -ctkd q4_0 -ctvd q4_0)
    case $1 in
        U0) $BC $UP/llama-server -m "$GGUF" --host 127.0.0.1 --port $PORT --no-webui > "$2" 2>&1 & ;;
        U1) $BC $PFX $UP/llama-server "${common[@]}" > "$2" 2>&1 & ;;
        T)  env LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_SERVER_CACHE_SHARE_MIN=1024 LLAMA_GPU_VERIFY=$TV \
                LLAMA_SERVER_REASONING_CONTROL=0 $TENV $BC $PFX $TK/llama-server "${common[@]}" \
                --spec-draft-vocab $H/draft_vocab_qwen38.txt --spec-draft-vocab-n 65536 \
                --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs ${TARGS:-} > "$2" 2>&1 & ;;
    esac
    pid=$!
    for _ in $(seq 600); do
        curl -sf "http://127.0.0.1:$PORT/health" > /dev/null && return 0
        kill -0 "$pid" 2>/dev/null || { wait "$pid" 2>/dev/null; pid=; return 1; }
        sleep 1
    done
    srv_stop; return 1
}
vram_row() {  # label extra-json
    local nctx
    nctx=$(curl -sf "http://127.0.0.1:$PORT/props" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("default_generation_settings",{}).get("n_ctx") or d.get("n_ctx"))' 2>/dev/null || echo "?")
    echo "{\"label\":\"$1\",\"vram_mb\":$(vram),\"n_ctx\":\"$nctx\",\"ctx_req\":$CTX,\"t\":\"$(date +%T)\"$2}" | tee -a "$L/vram.jsonl"
}
