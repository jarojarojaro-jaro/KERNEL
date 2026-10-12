#!/usr/bin/env bash
# One time-boxed generation block: start llama-server (user config: KV q4_0, MTP n=4, thinking low),
# generate until DEADLINE seconds, stop the server. Run under flock /tmp/gpu.lock.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
model=${MODEL:-$HOME/models/Qwen3.8-27B-UD-Q4_K_XL.gguf}
prompts=${1:?prompts.jsonl}
out=${2:?out.jsonl}
np=${NP:-4}
deadline=${DEADLINE:-480}
port=${PORT:-8099}
export LD_LIBRARY_PATH=$HOME/llama-opt/lib:/opt/rocm/core-10.0/lib
mkdir -p "$here/logs"
"$HOME/llama-opt/bin/llama-server" -m "$model" -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c $((np * 3072)) -np "$np" \
    --jinja --reasoning-effort "${EFFORT:-low}" --host 127.0.0.1 --port "$port" \
    --spec-type draft-mtp --spec-draft-n-max 4 \
    --spec-draft-vocab "$HOME/models/draft/draft_vocab_qwen38.txt" --spec-draft-vocab-n 65536 \
    > "$here/logs/server-gen.log" 2>&1 &
srv=$!
trap 'kill $srv 2>/dev/null; wait $srv 2>/dev/null' EXIT
for _ in $(seq 300); do
    curl -sf "http://127.0.0.1:$port/health" >/dev/null && break
    kill -0 $srv || { echo "server died"; tail -20 "$here/logs/server-gen.log"; exit 1; }
    sleep 1
done
"$HOME/qwen-opt/.venv-train/bin/python" "$here/gen.py" --prompts "$prompts" --out "$out" --port "$port" \
    --np "$np" --deadline "$deadline" --seed "${SEED:-1}"
