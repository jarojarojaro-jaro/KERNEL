#!/usr/bin/env bash
# Production launcher for OrcaCyber-Nano-1.0 on an RTX 3090 (CUDA), with the settings measured in report 56:
# full 262144 context on a q4_0 KV cache, MTP n=2 drafter, kvq-mma attention (GGML_CUDA_KVQ, PPL gate passed).
#   orca-serve.sh [np]        np = parallel slots (default 1; 2 gives +27-29% aggregate throughput per report 56)
# Stop: Ctrl-C or pkill -f 'bin/llama-server.*orca'
set -euo pipefail
ROOT=${ROOT:-$HOME/llama-orca}          # build tree with the orca-kvq (or newer) branch, installed via rbuild
BIN=$ROOT/bin
MODEL=${MODEL:-$HOME/models/orca-cyber-nano/OrcaCyber-Nano-1.0-AI-Defense-Mix-15.7G.gguf}
VOCAB=${VOCAB:-$HOME/models/draft/draft_vocab_qwen38.txt}
NP=${1:-1}
CTX=${CTX:-262144}
PORT=${PORT:-8080}

export LD_LIBRARY_PATH=$BIN:/opt/rocm/core-10.0/lib
export LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16
export LLAMA_GPU_VERIFY=1 LLAMA_SPEC_COUPLED=1
export LLAMA_SERVER_YIELD_FAST=2 LLAMA_TOKENIZE_PAR=8
export LLAMA_CKPT_VRAM=2
export LLAMA_CHAT_NATIVE=0                # Orca's own jinja template (vision macros), not native ChatML
export LLAMA_SERVER_SAFE_SPECIAL=1 LLAMA_SERVER_SAFE_TOOLS=1
export GGML_CUDA_KVQ=1                    # kvq-mma decode attention, +14% @23k depth, +21% @262k/29k
export LLAMA_MTP_REQUANT_CACHE=${LLAMA_MTP_REQUANT_CACHE:-$HOME/.cache/llama-mtp}
# No speculation (plain decode): GGML_CUDA_MMVQ_N1_ROWS=2 gives +2.5..7.7% (bit-exact); neutral with MTP.

exec "$BIN/llama-server" \
    -m "$MODEL" -fa on -ctk q4_0 -ctv q4_0 -c "$CTX" -np "$NP" -ngl 999 -fit off --jinja \
    --host 127.0.0.1 --port "$PORT" \
    --spec-type draft-mtp --spec-draft-n-max 2 -ctkd q4_0 -ctvd q4_0 \
    --spec-draft-vocab "$VOCAB" --spec-draft-vocab-n 65536 \
    --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs
