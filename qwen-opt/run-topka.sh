#!/usr/bin/env bash
# "Topka" build of the Qwen3.8-27B server: ~/llama-topka = amd-opt f61994f58 + lookup tail (6e12530cc)
# + prompt-cache share (50c3a2f2a), branch topka in ~/wt/topka. Wraps run-llm.sh (same flags, same port 8080)
# and only adds the switches below; the production build ~/llama-opt and run-llm.sh are untouched.
#
#   run-topka.sh [qwen|uncensored]
#
#   LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16  context lookup tail behind the MTP drafts, 16-wide verify, drafter-free
#                                               chains at T=0 (code edits / copies ~x2.4, chat unchanged; report 16b)
#   LLAMA_SERVER_CACHE_SHARE_MIN=1024           a new agent session reuses the cached system prompt after an unrelated
#                                               request (8.0 -> 1.6 s; report 16f E4)
#   GGML_HIP_PM4=0                              PM4 replay off: it causes GPU resets (report 17)
#   DRAFT_N=4                                   MTP draft length as in production
# Every switch can be overridden from the environment (e.g. LLAMA_SPEC_LOOKUP=0); other run-llm.sh variables
# (PORT, CTX, EFFORT, LOG, ...) pass through.
# Stop: Ctrl-C, or `pkill -f 'llama-topka/bin/llama-server'`. Back to production: ~/qwen-opt/run-llm.sh qwen
set -euo pipefail
model=${1:-qwen}
case $model in qwen|uncensored) ;; *) echo "unknown model: $model (qwen|uncensored)" >&2; exit 2 ;; esac
export ROCM_DIR=${ROCM_DIR:-$HOME/llama-topka}
export LLAMA_SPEC_LOOKUP=${LLAMA_SPEC_LOOKUP:-3}
export LLAMA_SPEC_LOOKUP_W=${LLAMA_SPEC_LOOKUP_W:-16}
export LLAMA_SERVER_CACHE_SHARE_MIN=${LLAMA_SERVER_CACHE_SHARE_MIN:-1024}
export GGML_HIP_PM4=${GGML_HIP_PM4:-0}
export DRAFT_N=${DRAFT_N:-4}
echo "run-topka: $model ROCM_DIR=$ROCM_DIR LLAMA_SPEC_LOOKUP=$LLAMA_SPEC_LOOKUP LLAMA_SPEC_LOOKUP_W=$LLAMA_SPEC_LOOKUP_W" \
     "LLAMA_SERVER_CACHE_SHARE_MIN=$LLAMA_SERVER_CACHE_SHARE_MIN GGML_HIP_PM4=$GGML_HIP_PM4 DRAFT_N=$DRAFT_N port ${PORT:-8080}" >&2
exec "$HOME/qwen-opt/run-llm.sh" "$model" mtp rocm
