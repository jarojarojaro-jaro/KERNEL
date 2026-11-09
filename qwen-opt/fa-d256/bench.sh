#!/usr/bin/env bash
# Step 6: llama-bench prefill at depth, ABBA A=VAR 0, B=BEST (same binary): pp512 @ d 4096 / 32768 / 131072,
# production model, KV q4_0, ub 512, -fa 1, PM4 off. -> res/bench.txt "test arm VAR avg_ts sd"
set -uo pipefail
. "$HOME/qwen-opt/fa-d256/common.sh"
[ -f "$D/res/BEST" ] || { echo "no BEST (selection: $(cat "$D/res/NONE" 2>/dev/null))"; exit 0; }
B=$(cat "$D/res/BEST")
trap 'pkill -f "llama-bench -m .*Qwen3.8" 2>/dev/null || true' EXIT
trap 'exit 1' TERM INT
export LD_LIBRARY_PATH=$BIN:/opt/rocm/core-10.0/lib
: > "$D/res/bench.txt"
for t in "d4k:-p 512 -n 0 -d 4096 -r 3" "d32k:-p 512 -n 0 -d 32768 -r 2" "d128k:-p 512 -n 0 -d 131072 -r 1"; do
    name=${t%%:*}; args=${t#*:}
    i=0
    for v in 0 $B $B 0; do
        i=$((i + 1))
        r=$(GGML_HIP_FA_D256_VAR=$v taskset -c 2-5 "$BIN/llama-bench" -m "$M" -ngl 999 -fa 1 -ctk q4_0 -ctv q4_0 -ub 512 \
            -o csv $args 2>"$D/logs/bench-$name-$i.err" | tail -1 | awk -F, '{gsub(/"/,""); print $(NF-1), $NF}')
        echo "$name $i $v $r" | tee -a "$D/res/bench.txt"
    done
done
