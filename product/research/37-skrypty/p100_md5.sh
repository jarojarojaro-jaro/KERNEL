#!/usr/bin/env bash
# Report 37 gate: greedy md5 (fusion/greedy.sh) of BIN with the topka env plus each ARM_ENV.
# Expected = production: Qwen plain c4708318, MTP 6f14e814; LFM plain 894e56e4 (when LFM=1).
# All OK -> /tmp/p100-gate/<TAG>.PASS, else removed (the A/B jobs of that item skip). Run ONLY from the GPU queue.
# usage: p100_md5.sh TAG BIN_DIR "ARM_ENV" ["ARM_ENV"...]      (env LFM=1 also checks LFM per arm)
set -uo pipefail
tag=$1; bin=$2; shift 2
[ -x "$bin/llama-server" ] || bin=$bin/bin
g=/tmp/p100-gate; mkdir -p $g; rm -f "$g/$tag.PASS"
trap 'pkill -f "$bin/llama-server"' EXIT
trap 'exit 1' TERM INT
pkill -f 'llama-topka/bin/llama-server' && sleep 5
"$HOME/qwen-opt/lookup/vram_ok.sh" || exit 1
export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0 LLAMA_GPU_VERIFY=1 LLAMA_SPEC_LOOKUP=3 \
    LLAMA_SPEC_LOOKUP_W=16 LLAMA_SPEC_COUPLED=1 LLAMA_SERVER_YIELD_FAST=2 GGML_HIP_PM4_MIN_DISPATCH=16 \
    GGML_HIP_PM4_LAZY_EXEC=1 PORT=18861
o=/tmp/p100-md5/$tag; mkdir -p $o; rm -f $o/*
a=0; bad=0
for envs in "$@"; do
    a=$((a + 1))
    env $envs taskset -c 2-5 "$HOME/qwen-opt/fusion/greedy.sh" "$bin" "$bin" "$o/qwen-a$a" qwen > /dev/null
    [ "${LFM:-0}" = 1 ] && env $envs MODES=plain taskset -c 2-5 "$HOME/qwen-opt/fusion/greedy.sh" "$bin" "$bin" "$o/lfm-a$a" lfm > /dev/null
    n=0
    for f in $o/qwen-a$a.*.txt $o/lfm-a$a.*.txt; do
        [ -f "$f" ] || continue; n=$((n + 1))
        m=$(md5sum < "$f" | cut -c1-8)
        case ${f##*/} in lfm-*) want=894e56e4 ;; *.mtp.txt) want=6f14e814 ;; *) want=c4708318 ;; esac
        [ "$m" = "$want" ] && echo "arm $a [$envs] ${f##*/}: $m OK" || { echo "arm $a [$envs] ${f##*/}: $m MISMATCH (want $want)"; bad=1; }
    done
    [ $n -ge 2 ] || { echo "arm $a: only $n outputs"; bad=1; }
done
[ $bad = 1 ] && { echo "MD5 FAIL $tag"; exit 1; }
touch "$g/$tag.PASS"; echo "MD5 OK $tag"
