# Sourced by the K-018 / K-019 / K-020 / K-038 arm scripts (2026-11-25). One test llama-server with the production
# config of `run-topka.sh uncensored` (topka-q70: flags and env written out here, so $! is the llama-server PID),
# engine $BIN (default ~/wt/qprep-spec/build-hip/bin: topka-q70 3191b25f4 + the K-018/K-019/K-020 switches, all off by
# default), port $PORT (default 18796), CPUs 2-5. Arm switches come from the caller's environment on top.
#   srv_start LABEL DIR    -> $SRV = server pid, log DIR/LABEL.server.log; returns 1 when /health does not come up
#   srv_stop               ONE SIGTERM after the slot is idle, 60 s, then SIGKILL
# Overrides: CACHE_RAM (MiB, default 40960), DRAFT_N (4), KVD (draft KV type, q4_0), CTX (262144).
# Sourcing sets `trap srv_kill EXIT` (kills whatever listens on the port, also after the queue's SIGTERM).
BIN=${BIN:-$HOME/wt/qprep-spec/build-hip/bin}
PORT=${PORT:-18796}
srv_kill() { pkill -9 -f "port $PORT( |$)" 2>/dev/null || true; }
srv_start() {
    local label=$1 dir=$2
    mkdir -p "$dir"
    # production PM4 config (run-topka.sh), explicit
    export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0
    unset QUEUE_PM4_SAFETY
    export GGML_HIP_FA_D256_VAR=${GGML_HIP_FA_D256_VAR:-83}
    export LLAMA_SERVER_CACHE_HUGE=${LLAMA_SERVER_CACHE_HUGE:-1}
    export LLAMA_SPEC_LOOKUP=${LLAMA_SPEC_LOOKUP:-3} LLAMA_SPEC_LOOKUP_W=${LLAMA_SPEC_LOOKUP_W:-16}
    export LLAMA_SERVER_CACHE_SHARE_MIN=${LLAMA_SERVER_CACHE_SHARE_MIN:-1024}
    export LLAMA_MTP_REQUANT_CACHE=${LLAMA_MTP_REQUANT_CACHE-$HOME/.cache/llama-mtp}
    export LLAMA_GPU_VERIFY=${LLAMA_GPU_VERIFY:-1} LLAMA_SPEC_COUPLED=${LLAMA_SPEC_COUPLED:-1}
    export LLAMA_SERVER_YIELD_FAST=${LLAMA_SERVER_YIELD_FAST:-2}
    export GGML_HIP_PM4_MIN_DISPATCH=${GGML_HIP_PM4_MIN_DISPATCH:-16} GGML_HIP_PM4_LAZY_EXEC=${GGML_HIP_PM4_LAZY_EXEC:-1}
    export LLAMA_SERVER_SAFE_SPECIAL=${LLAMA_SERVER_SAFE_SPECIAL:-1} LLAMA_SERVER_SAFE_TOOLS=${LLAMA_SERVER_SAFE_TOOLS:-1}
    export LLAMA_TOKENIZE_PAR=${LLAMA_TOKENIZE_PAR:-8} LLAMA_CKPT_VRAM=${LLAMA_CKPT_VRAM:-2}
    export LLAMA_CHAT_NATIVE=${LLAMA_CHAT_NATIVE:-1} LLAMA_CHAT_LATE_SYSTEM=${LLAMA_CHAT_LATE_SYSTEM:-1}
    export LLAMA_SERVER_REASONING_CONTROL=0
    local kvd=${KVD:-q4_0}
    "$HOME/qwen-opt/lookup/vram_ok.sh" || return 1
    env | grep -E '^(LLAMA_|GGML_|HSA_)' | sort > "$dir/$label.env"
    LD_LIBRARY_PATH=$BIN:/opt/rocm/core-10.0/lib taskset -c 2-5 "$BIN/llama-server" \
        -m "$HOME/models/orca/Qwen3.8-27B-Uncensored-Q4_K_M.gguf" -ngl 999 -fa on -ctk q4_0 -ctv q4_0 \
        -c "${CTX:-262144}" -np 1 --jinja --cache-ram "${CACHE_RAM:-40960}" --reasoning-effort low \
        --host 127.0.0.1 --port "$PORT" --log-file "$dir/$label.server.log" \
        --spec-type draft-mtp --spec-draft-n-max "${DRAFT_N:-4}" \
        --spec-draft-vocab "$HOME/models/draft/draft_vocab_qwen38.txt" --spec-draft-vocab-n 65536 \
        --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs -ctkd "$kvd" -ctvd "$kvd" \
        > "$dir/$label.stdout" 2>&1 < /dev/null &
    SRV=$!
    for _ in $(seq 300); do
        curl -sf "127.0.0.1:$PORT/health" > /dev/null && break
        kill -0 "$SRV" 2>/dev/null || { echo "$label: server died"; tail -20 "$dir/$label.stdout"; return 1; }
        sleep 1
    done
    curl -sf "127.0.0.1:$PORT/health" > /dev/null || { echo "$label: no /health after 300 s"; return 1; }
    echo "$label: server pid $SRV up $(date +%T), bin $BIN"
}
srv_stop() {
    for _ in $(seq 60); do curl -s -m 2 "127.0.0.1:$PORT/slots" 2>/dev/null | grep -q '"is_processing":true' || break; sleep 1; done
    kill -TERM "$SRV" 2>/dev/null
    for _ in $(seq 60); do kill -0 "$SRV" 2>/dev/null || break; sleep 1; done
    kill -KILL "$SRV" 2>/dev/null || true
    wait "$SRV" 2>/dev/null || true
}
# the queue timeout sends SIGTERM to the arm: exit through the EXIT trap (srv_kill) instead of dying with the server up
trap srv_kill EXIT
trap "exit 1" TERM INT
