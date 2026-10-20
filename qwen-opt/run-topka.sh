#!/usr/bin/env bash
# "Topka" build of the Qwen3.8-27B server: ~/llama-topka = topka 2821e1303 (amd-opt f61994f58 + lookup tail
# + prompt-cache share + PM4 WA=2/GUARD), staged ~/wt/topka/inst, installed 2026-10-19 19:4x
# branch topka in ~/wt/topka. Wraps run-llm.sh (same flags, same port 8080)
# and only adds the switches below; the production build ~/llama-opt and run-llm.sh are untouched.
#
#   run-topka.sh [qwen|uncensored|lfm|lfm-uncensored]
#
#   LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16  context lookup tail behind the MTP drafts, 16-wide verify, drafter-free
#                                               chains at T=0 (code edits / copies ~x2.4, chat unchanged; report 16b)
#   LLAMA_SERVER_CACHE_SHARE_MIN=1024           a new agent session reuses the cached system prompt after an unrelated
#                                               request (8.0 -> 1.6 s; report 16f E4)
#   GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2           PM4 replay with the GFX11 PRIV fix + in-tape guard; HSA_USE_SVM=0 cuts
#   GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0          queue evictions 446 -> 18. S6 soak 1205 requests, 0 faults; ABBA:
#                                               Qwen spec_sweep T=1 111.0/110.8 -> 115.3/115.8 t/s (+4.2%), LFM tg128
#                                               266.4/266.2 -> 295.7/296.2 (+11.1%); md5 unchanged (report 17 §9-10)
#   LLAMA_GPU_VERIFY=1                          top-128 candidates of each verify row computed on the GPU, only those
#                                               cross PCIe (no 16 MB logits copy, no CPU full-row scan): mvs +2.4%,
#                                               copy +2.2%, chat +0.5%, output identical at T=0 and T=1 (report 24m)
#   DRAFT_N=4                                   MTP draft length as in production
#   DRAFT_N=5 (opt-in, T=0 thinking/reasoning)  config profile for greedy reasoning text (LocalMaxxing reasoning-v1/code-v1
#                                               class): reasoning-v1 144.4 -> 154.2 t/s (+6.8%), code-v1 124.1 -> 127.4
#                                               (+2.7%), deterministic in 3 runs; chat T=1 +1.4% [-2.4, +5.4], mvs -2.1%
#                                               [-5.3, +1.2], so not the default. CONFIG change: greedy MTP md5 d71a2c04
#                                               (n=4: 6f14e814), GPU verify off == on (report 35 E1)
# LFM profile (lfm|lfm-uncensored; no MTP head, run-llm.sh <model> none rocm):
#   -b 2048 -ub 2048 (EXTRA_ARGS)               prefill pp4096 6108 -> 7148 t/s (+17%), TTFT 8k/32k -15%, +0.5 GB VRAM
#                                               (report 16f E1). KLD ub 2048 vs 512 = 0.068, the same as between ANY two
#                                               ubatch sizes (1024: 0.067, 256: 0.055; A/A 0.000), PPL 14.11 vs 14.30
#                                               (+-0.45): LFM reacts to every ubatch split, 2048 is not worse. UB=512 old.
#   LLAMA_SPEC_LOOKUP=0                         the lookup alone (no drafter) is not adopted for LFM (report 24d)
#   LLAMA_SERVER_CACHE_SHARE_MIN=1024 and the PM4 switches as for Qwen (16f E4: new LFM session 1357 -> 230 ms)
# Every switch can be overridden from the environment (e.g. LLAMA_SPEC_LOOKUP=0); other run-llm.sh variables
# (PORT, CTX, EFFORT, LOG, ...) pass through.
# Stop: Ctrl-C, or `pkill -f 'llama-topka/bin/llama-server'`. Back to production: ~/qwen-opt/run-llm.sh qwen
set -euo pipefail
# The live server must never inherit a lock fd from whoever (re)started it: an agent restarting topka
# inside its `flock /tmp/gpu.lock …` hold made this long-running server hold the GPU lock forever and
# deadlocked every GPU job (2026-10-19). Close every fd above 2 before anything else.
for fd in /proc/$$/fd/*; do fd=${fd##*/}; [ "$fd" -gt 2 ] 2>/dev/null && eval "exec $fd>&-" 2>/dev/null || true; done
model=${1:-qwen}
case $model in qwen|uncensored|lfm|lfm-uncensored) ;; *) echo "unknown model: $model (qwen|uncensored|lfm|lfm-uncensored)" >&2; exit 2 ;; esac
spec=mtp
lookup_default=3
coupled_default=1   # LLAMA_SPEC_COUPLED: Gumbel-coupled draft sampling, T=1 +3.5% (CI +1.8..+5.3), same distribution, T=0 md5 unchanged (report 24p)
hostgap_default=1   # host-gap switches (report 24o): chat T=1 113.0 -> 114.6 t/s on topka-next (coupled both arms), md5 on == off
case $model in
    lfm|lfm-uncensored)
        spec=none
        lookup_default=0
        coupled_default=0
        hostgap_default=0
        export EXTRA_ARGS=${EXTRA_ARGS:-"-b,2048,-ub,${UB:-2048}"} ;;
esac
export ROCM_DIR=${ROCM_DIR:-$HOME/llama-topka}
export LLAMA_SPEC_LOOKUP=${LLAMA_SPEC_LOOKUP:-$lookup_default}
export LLAMA_SPEC_LOOKUP_W=${LLAMA_SPEC_LOOKUP_W:-16}
export LLAMA_SERVER_CACHE_SHARE_MIN=${LLAMA_SERVER_CACHE_SHARE_MIN:-1024}
# The queue's PM4-off safety default (QUEUE_PM4_SAFETY=1) must not leak into the production config. A caller that
# really wants topka with PM4 off inside the queue sets GGML_HIP_PM4=0 AND unsets QUEUE_PM4_SAFETY.
[ "${QUEUE_PM4_SAFETY:-0}" = 1 ] && [ "${GGML_HIP_PM4:-}" = 0 ] && unset GGML_HIP_PM4
export GGML_HIP_PM4=${GGML_HIP_PM4:-1}
export GGML_HIP_PM4_WA=${GGML_HIP_PM4_WA:-2}
export GGML_HIP_PM4_GUARD=${GGML_HIP_PM4_GUARD:-1}
export HSA_USE_SVM=${HSA_USE_SVM:-0}
export LLAMA_GPU_VERIFY=${LLAMA_GPU_VERIFY:-1}
export LLAMA_SPEC_COUPLED=${LLAMA_SPEC_COUPLED:-$coupled_default}
if [ "${HOSTGAP:-$hostgap_default}" = 1 ]; then
    export LLAMA_SERVER_YIELD_FAST=${LLAMA_SERVER_YIELD_FAST:-2}
    export GGML_HIP_PM4_MIN_DISPATCH=${GGML_HIP_PM4_MIN_DISPATCH:-16}
    export GGML_HIP_PM4_LAZY_EXEC=${GGML_HIP_PM4_LAZY_EXEC:-1}
fi
export DRAFT_N=${DRAFT_N:-4}
echo "run-topka: $model ROCM_DIR=$ROCM_DIR LLAMA_SPEC_LOOKUP=$LLAMA_SPEC_LOOKUP LLAMA_SPEC_LOOKUP_W=$LLAMA_SPEC_LOOKUP_W" \
     "LLAMA_SERVER_CACHE_SHARE_MIN=$LLAMA_SERVER_CACHE_SHARE_MIN GGML_HIP_PM4=$GGML_HIP_PM4 WA=$GGML_HIP_PM4_WA" \
     "GUARD=$GGML_HIP_PM4_GUARD HSA_USE_SVM=$HSA_USE_SVM LLAMA_GPU_VERIFY=$LLAMA_GPU_VERIFY COUPLED=$LLAMA_SPEC_COUPLED DRAFT_N=$DRAFT_N spec=$spec" \
     "EXTRA_ARGS=${EXTRA_ARGS:-} port ${PORT:-8080}" >&2
exec "$HOME/qwen-opt/run-llm.sh" "$model" "$spec" rocm
