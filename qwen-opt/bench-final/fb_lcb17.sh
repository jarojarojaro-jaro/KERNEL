#!/usr/bin/env bash
# Today's rerun of the NOTES.md:331 record (long_ctx_bench.py, default depths 8000,32000,100000,190000 -> prompts
# ~1.7k/6.6k/29.5k/94k tokens, T=0, 256 tokens, thinking off) on the topka binary with the exact run-llm.sh qwen server
# args (via long_ctx_bench, which adds -np 1 --no-webui) and the run-topka.sh environment.
# Two arms on fresh servers: W16 = topka as run (LOOKUP=3 W=16), MTP = topka with LLAMA_SPEC_LOOKUP=0 (MTP n=4 only,
# like the 2026-10 record). long_ctx_bench's port 8095 is overridden to 18704. Run ONLY from run-jobs.sh.
# Output: ~/qwen-opt/long_ctx.jsonl (labels fb-lcb-*), server logs ~/qwen-opt/logs/fb-lcb-*.log
set -euo pipefail
port=18704
trap 'pkill -f "llama-server.*--port $port" 2>/dev/null || true; for _ in $(seq 30); do pgrep -f "llama-server.*--port $port" > /dev/null || break; sleep 1; done; pkill -9 -f "llama-server.*--port $port" 2>/dev/null || true' EXIT
trap 'exit 1' TERM INT
pkill -f 'llama-topka/bin/llama-server.*--port 8080' && sleep 5 || true
M=$HOME/models
args=(-m "$M/Qwen3.8-27B-UD-Q4_K_XL.gguf" -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c 204800 --jinja --cache-ram 16384
      --reasoning-effort low --spec-type draft-mtp --spec-draft-n-max 4 --spec-draft-vocab "$M/draft/draft_vocab_qwen38.txt"
      --spec-draft-vocab-n 65536 --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs -ctkd q4_0 -ctvd q4_0)
for arm in W16 MTP; do
    "$HOME/qwen-opt/lookup/vram_ok.sh"
    case $arm in W16) lk=3 ;; MTP) lk=0 ;; esac
    cd "$HOME/qwen-opt" && env LD_LIBRARY_PATH="$HOME/llama-topka/lib:/opt/rocm/core-10.0/lib" \
        GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0 LLAMA_GPU_VERIFY=1 \
        LLAMA_SPEC_LOOKUP=$lk LLAMA_SPEC_LOOKUP_W=16 LLAMA_SERVER_CACHE_SHARE_MIN=1024 LLAMA_SERVER_REASONING_CONTROL=0 \
        taskset -c 2-5 .venv/bin/python -c "import sys; sys.argv[0] = 'long_ctx_bench.py'; import long_ctx_bench as L; L.PORT = $port; L.main()" \
        --label "fb-lcb17-$arm" --depths 2000 --bin "$HOME/llama-topka/bin/llama-server" -- "${args[@]}"
done
