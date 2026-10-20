#!/usr/bin/env bash
# Report 40: mtp_extract (built against topka: mtp_extract_topka) on the E0 outputs (pa_extract_prep.py -> DIR/seqs.bin):
# target h_nextn + target top-32 + the server-path greedy MTP chain per response position, KV q4_0 / draft KV q4_0 as
# in production (MTP block in its file types Q6_K/Q8_0, not the IQ4_XS requant). Run ONLY from the GPU queue.
# usage: pa_extract.sh DIR
set -euo pipefail
dir=$1
export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0
export LD_LIBRARY_PATH=$HOME/llama-topka/bin:/opt/rocm/core-10.0/lib
pkill -f 'llama-topka/bin/llama-server' && sleep 5 || true
"$HOME/qwen-opt/lookup/vram_ok.sh"
cd "$HOME/qwen-opt/prose-accept"
time ./mtp_extract_topka -m "$HOME/models/Qwen3.8-27B-UD-Q4_K_XL.gguf" --vocab "$HOME/models/draft/draft_vocab_qwen38.txt" \
    --in "$dir/seqs.bin" --out "$dir" -c 8192 --kv q4_0 --kv-dft q4_0 --parity-seqs 0
ls -la "$dir"
