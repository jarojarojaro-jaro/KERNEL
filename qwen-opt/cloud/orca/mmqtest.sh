#!/usr/bin/env bash
# MMQ IQ4_XS occupancy 2 vs baseline: interleaved pp2048 A/B + PPL gate (both binaries in the same tree)
set -u
BASE=/root/w/fork/build/bin-base
VAR=/root/w/fork/build/bin
M=/root/models/OrcaCyber-Nano-1.0-AI-Defense-Mix-15.7G.gguf
RES=/root/results/$(date +%Y%m%d-%H%M)/mmq
mkdir -p "$RES"
pp() { local bin=$1; LD_LIBRARY_PATH=$bin $bin/llama-bench -m "$M" -p 2048 -n 0 -r 3 -fa on -ctk q4_0 -ctv q4_0 -ngl 999 \
        -o jsonl 2>/dev/null | python3 -c "import sys,json;print('%.0f' % json.loads(sys.stdin.readline())['avg_ts'])"; }
ppl() { local bin=$1; LD_LIBRARY_PATH=$bin timeout 120 $bin/llama-perplexity -m "$M" -f /root/cloud/corpus.txt \
        -c 4096 -ngl 999 -fa on -ctk q4_0 -ctv q4_0 --chunks 3 2>/dev/null | grep -oE "\[[0-9]+\][0-9.]+|nan" | tr '\n' ' '; }
for i in 1 2; do
    printf 'pp2048 base%s %s\n' "$i" "$(pp $BASE)"
    printf 'pp2048 mmq%s  %s\n'  "$i" "$(pp $VAR)"
done
printf 'ppl base %s\n' "$(ppl $BASE)"
printf 'ppl mmq  %s\n' "$(ppl $VAR)"
echo done
