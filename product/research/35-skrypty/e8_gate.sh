#!/usr/bin/env bash
# Report 35 E8 gate (39a E1, Maya #285): greedy md5 of the first requests after start, cold vs one 1100-token warm-up
# prompt (greedy.sh WARM=1): Qwen plain + MTP n=4 and LFM plain on ~/llama-topka. Run ONLY from the GPU queue.
set -uo pipefail
bin=$HOME/llama-topka/bin
export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0 PORT=18724
trap 'pkill -f "$bin/llama-server.*--port $PORT" || true' EXIT
trap 'exit 1' TERM INT
pkill -f 'llama-topka/bin/llama-server' && sleep 5
"$HOME/qwen-opt/lookup/vram_ok.sh" || exit 1
mkdir -p /tmp/x35 && rm -f /tmp/x35/w-*.txt
g() { WARM=$1 MODES="$3" taskset -c 2-5 "$HOME/qwen-opt/fusion/greedy.sh" "$bin" "$bin" "/tmp/x35/w-$2-w$1" $2 > /dev/null 2>&1; }
g 0 qwen "plain mtp"; g 1 qwen "plain mtp"; g 0 lfm plain; g 1 lfm plain
for f in /tmp/x35/w-*.txt; do echo "$(md5sum < "$f" | cut -c1-8) $(basename "$f")"; done
rc=0
for t in qwen-w%s.plain qwen-w%s.mtp lfm-w%s.plain; do
    a=/tmp/x35/w-$(printf $t 0).txt; b=/tmp/x35/w-$(printf $t 1).txt
    [ -s "$a" ] && cmp -s "$a" "$b" && echo "$(printf $t x): warm == cold" || { echo "$(printf $t x): warm != cold"; rc=1; }
done
exit $rc
