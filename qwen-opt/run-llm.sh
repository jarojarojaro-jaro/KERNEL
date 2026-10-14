#!/usr/bin/env bash
# Start the optimized llama-server on the RX 7900 XTX.
#
#   run-llm.sh [qwen|uncensored|lfm|lfm-uncensored] [mtp|dflash|none] [rocm|vulkan]
#
# Measured 2026-10-14 (ROCm, ctx 204800, KV q4_0, MTP n=4 + 64k draft vocab, IQ4_XS draft, 6 EN/PL prompts, T=1):
#   qwen        mtp  rocm   ~104 t/s  (default; ~96 t/s with 94k tokens in context)
#   uncensored  mtp  rocm   ~106 t/s  orcarouter Qwen3.8-27B-Uncensored Q4_K_M (abliterated); VISION=1 adds mmproj
#   qwen        mtp  vulkan optional backend, slower on long prompts
#   lfm         none ~240 t/s LiquidAI LFM2.5-24B-A2B Q5_K_M (MoE, ~2B active, no MTP head), ctx 131072, KV q8_0
#   lfm-uncensored    same settings; AtomicChat abliterated LFM2.5-24B-A2B AD-Q5_K_M (refusal edit in blocks 14-39)
#
# env: CTX (default 204800), PORT (default 8080), HOST (default 127.0.0.1), KV (default q4_0; q8_0 for lfm),
#      EFFORT thinking length: low (default), medium, xhigh (model default, long thinking), off (no thinking)
#      LOG server log file (default ~/qwen-opt/logs/server-<time>.log, newest linked as logs/latest.log)
#      DRAFT_N max draft tokens (default: backend/drafter specific), P_MIN stop drafting below this draft confidence
#      DRAFT_SAMPLING greedy (default) | probabilistic (MTP samples drafts, target verifies by rejection sampling)
#      ROCM_DIR install prefix of the ROCm build (default ~/llama-opt; bin/ and lib/)
set -euo pipefail

model=${1:-qwen}
extra_args_raw=${EXTRA_ARGS:-}
extra_args=(${extra_args_raw//,/ })
default_spec=mtp
case $model in lfm|lfm-uncensored) default_spec=none ;; esac
spec=${2:-$default_spec}
backend=${3:-rocm}
ctx_default=204800
case $model in lfm|lfm-uncensored) ctx_default=131072 ;; esac
ctx=${CTX:-$ctx_default}
port=${PORT:-8080}
host=${HOST:-127.0.0.1}
# LFM has only 10 attention layers, so a q8_0 KV cache costs ~1.4 GB at 131k and buys accuracy
kv_default=q4_0
case $model in lfm|lfm-uncensored) kv_default=q8_0 ;; esac
kv=${KV:-$kv_default}
effort=${EFFORT:-low}
mkdir -p "$HOME/qwen-opt/logs"
log=${LOG:-$HOME/qwen-opt/logs/server-$(date +%F_%H%M%S).log}
ln -sfn "$log" "$HOME/qwen-opt/logs/latest.log"

# Qwen3.8 templates accept low|medium|xhigh; off disables thinking entirely. LFM has no effort levels.
case $effort in
    low|medium|xhigh) think_args=(--reasoning-effort "$effort") ;;
    off) think_args=(--reasoning off) ;;
    *) echo "unknown EFFORT: $effort (low|medium|xhigh|off)" >&2; exit 2 ;;
esac
case $model in lfm|lfm-uncensored) think_args=() ;; esac

models=$HOME/models
drafter=$models/draft/Qwen3.8-27B-DFlash2-Q4_K_M.gguf
draft_vocab=$models/draft/draft_vocab_qwen38.txt

case $model in
    qwen)       gguf=$models/Qwen3.8-27B-UD-Q4_K_XL.gguf ;;
    uncensored) gguf=$models/orca/Qwen3.8-27B-Uncensored-Q4_K_M.gguf
                [ "${VISION:-0}" = 1 ] && extra_args=(--mmproj "$models/orca/mmproj-Qwen3.8-27B-Uncensored-f16.gguf") ;;
    lfm)        gguf=$models/lfm/LFM2.5-24B-A2B-Q5_K_M.gguf ;;
    lfm-uncensored) gguf=$models/lfm/LFM2.5-24B-A2B-Uncensored-AD-Q5_K_M.gguf ;;
    *) echo "unknown model: $model (qwen|uncensored|lfm|lfm-uncensored)" >&2; exit 2 ;;
esac

case $backend in
    vulkan)
        # user-space Mesa RADV + LunarG loader (no root install needed)
        vkbin=${VK_BIN:-$HOME/llama-opt-vk/bin}
        bin=$vkbin/llama-server
        export VK_ICD_FILENAMES=$HOME/llama-opt-vk/radeon_icd.json
        export LD_LIBRARY_PATH=$vkbin:$HOME/vk/1.4.363.0/x86_64/lib/VulkanLoader/lib:$HOME/vk/root/usr/lib/x86_64-linux-gnu
        mtp_n=5 ;;
    rocm)
        rocm_dir=${ROCM_DIR:-$HOME/llama-opt}
        bin=$rocm_dir/bin/llama-server
        export LD_LIBRARY_PATH=$rocm_dir/lib:/opt/rocm/core-10.0/lib
        mtp_n=4 ;;
    *) echo "unknown backend: $backend (vulkan|rocm)" >&2; exit 2 ;;
esac

case $spec in
    # DFlash2 block drafter: 6 draft tokens (verify batch = 7)
    dflash) spec_args=(-md "$drafter" -ngld 99 --spec-type draft-dflash --spec-draft-n-max "${DRAFT_N:-6}") ;;
    # built-in MTP head (Qwen only) with the reduced-vocabulary draft head
    mtp)    spec_args=(--spec-type draft-mtp --spec-draft-n-max "${DRAFT_N:-$mtp_n}"
                       --spec-draft-vocab "$draft_vocab" --spec-draft-vocab-n 65536
                       --spec-draft-head-type "${MTP_TYPE:-iq4_xs}" --spec-mtp-type "${MTP_TYPE:-iq4_xs}"
                       -ctkd "$kv" -ctvd "$kv") ;;
    none)   spec_args=() ;;
    *) echo "unknown spec: $spec (mtp|dflash|none)" >&2; exit 2 ;;
esac
[ -n "${P_MIN:-}" ] && spec_args+=(--spec-draft-p-min "$P_MIN")
[ -n "${DRAFT_SAMPLING:-}" ] && spec_args+=(--spec-draft-sampling "$DRAFT_SAMPLING")

# Runtime suspend (BACO) evicts VRAM to system RAM and the model then runs over PCIe (~4 t/s).
# The proper fix is power/control=on (gpu-powercap.service); otherwise hold a KFD context for the
# server's lifetime, which blocks runtime suspend.
if [ "$(cat /sys/class/drm/card0/device/power/control)" != on ]; then
    echo "GPU runtime suspend is enabled; holding the GPU awake with gpu-keepawake" >&2
    LD_LIBRARY_PATH=/opt/rocm/core-10.0/lib "$HOME/qwen-opt/gpu-keepawake/keepawake" >/dev/null &
    keepawake=$!
    trap 'kill $keepawake 2>/dev/null' EXIT
    sleep 2
fi

"$bin" -m "$gguf" -ngl 999 -fa on -ctk "$kv" -ctv "$kv" -c "$ctx" -np 1 --jinja --cache-ram 16384 \
    "${think_args[@]}" --host "$host" --port "$port" --log-file "$log" "${spec_args[@]}" "${extra_args[@]}"
