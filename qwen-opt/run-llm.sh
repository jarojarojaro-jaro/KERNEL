#!/usr/bin/env bash
# Start the optimized llama-server on the RX 7900 XTX.
#
#   run-llm.sh [qwen|saluki] [mtp|dflash|none] [vulkan|rocm]
#
# Measured at ctx 204800, KV q4_0, EN+PL prompt mix (old build, MTP n=3: 59 t/s):
#   qwen  mtp  vulkan  ~92 t/s  (default; MTP n=5, 64k-token draft head)
#   qwen  mtp  rocm    ~86 t/s  (patched HIP kernels; prompt processing ~1.2-1.4x faster than Vulkan)
#   qwen  dflash       fastest for English/code (~120 t/s) but weak on Polish (PL prose ~40 t/s)
#   saluki has no MTP head, so it defaults to dflash
#
# env: CTX (default 204800), PORT (default 8080), HOST (default 127.0.0.1), KV (default q4_0)
set -euo pipefail

model=${1:-qwen}
default_spec=mtp
[ "$model" = saluki ] && default_spec=dflash
spec=${2:-$default_spec}
backend=${3:-vulkan}
ctx=${CTX:-204800}
port=${PORT:-8080}
host=${HOST:-127.0.0.1}
kv=${KV:-q4_0}

models=$HOME/models
drafter=$models/draft/Qwen3.8-27B-DFlash2-Q4_K_M.gguf
draft_vocab=$models/draft/draft_vocab_qwen38.txt

case $model in
    qwen)   gguf=$models/Qwen3.8-27B-UD-Q4_K_XL.gguf ;;
    saluki) gguf=$models/Underdog-Saluki-27B-1.0-IQ2-mix.gguf ;;
    *) echo "unknown model: $model (qwen|saluki)" >&2; exit 2 ;;
esac

case $backend in
    vulkan)
        # user-space Mesa RADV + LunarG loader (no root install needed)
        bin=$HOME/llama-opt-vk/bin/llama-server
        export VK_ICD_FILENAMES=$HOME/llama-opt-vk/radeon_icd.json
        export LD_LIBRARY_PATH=$HOME/llama-opt-vk/bin:$HOME/vk/1.4.363.0/x86_64/lib/VulkanLoader/lib:$HOME/vk/root/usr/lib/x86_64-linux-gnu
        mtp_n=5 ;;
    rocm)
        bin=$HOME/llama-opt/bin/llama-server
        export LD_LIBRARY_PATH=$HOME/llama-opt/lib:/opt/rocm/core-10.0/lib
        mtp_n=4 ;;
    *) echo "unknown backend: $backend (vulkan|rocm)" >&2; exit 2 ;;
esac

case $spec in
    # DFlash2 block drafter: 6 draft tokens (verify batch = 7)
    dflash) spec_args=(-md "$drafter" -ngld 99 --spec-type draft-dflash --spec-draft-n-max 6) ;;
    # built-in MTP head (Qwen only) with the reduced-vocabulary draft head
    mtp)    [ "$model" = qwen ] || { echo "saluki has no MTP head, use dflash" >&2; exit 2; }
            spec_args=(--spec-type draft-mtp --spec-draft-n-max "$mtp_n"
                       --spec-draft-vocab "$draft_vocab" --spec-draft-vocab-n 65536) ;;
    none)   spec_args=() ;;
    *) echo "unknown spec: $spec (mtp|dflash|none)" >&2; exit 2 ;;
esac

exec "$bin" -m "$gguf" -ngl 999 -fa on -ctk "$kv" -ctv "$kv" -c "$ctx" -np 1 --jinja \
    --host "$host" --port "$port" "${spec_args[@]}"
