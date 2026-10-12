#!/usr/bin/env bash
# Start llama-server from a build dir with the production speculative flags (foreground).
# usage: server.sh BIN_DIR LIB_DIR MODEL(qwen|unc) PORT [CTX] [extra args...]
set -euo pipefail
bin=$1; lib=$2; model=$3; port=$4; ctx=${5:-204800}; shift 5 || shift $#
case $model in
    qwen) gguf=$HOME/models/Qwen3.8-27B-UD-Q4_K_XL.gguf ;;
    unc)  gguf=$HOME/models/orca/Qwen3.8-27B-Uncensored-Q4_K_M.gguf ;;
esac
export LD_LIBRARY_PATH=$lib:/opt/rocm/core-10.0/lib
exec "$bin/llama-server" -m "$gguf" -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c "$ctx" -np 1 --jinja \
    --reasoning-effort low --spec-type draft-mtp --spec-draft-n-max 4 \
    --spec-draft-vocab "$HOME/models/draft/draft_vocab_qwen38.txt" --spec-draft-vocab-n 65536 \
    --host 127.0.0.1 --port "$port" --no-webui "$@"
