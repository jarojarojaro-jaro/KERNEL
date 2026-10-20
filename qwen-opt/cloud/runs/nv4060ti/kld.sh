#!/usr/bin/env bash
# ON the box: KLD gate of a numerics-changing switch (report 31). kld.sh <label> <ENV=val ...>
# Reference = X2 with every switch off (same binary); candidate = X2 with the given env. wikitext-2 test, -c 512,
# 8 chunks, -b 512 (one sequence per ubatch, the GDN MMA case), KV q4_0 like production. Logs in /root/res/gate/kld.*; gate via kld_gate.py.
set -uo pipefail
label=$1; shift
B=/root/bin/X2; G=/root/res/gate; M=/root/models/Qwen3.8-27B-UD-IQ4_XS.gguf
base=(-m $M -f /root/wiki.test.raw -c 512 --chunks 8 -b 512 -ub 512 -ngl 99 -fa on -ctk q4_0 -ctv q4_0 -t 4)
if [ ! -f $G/kld.ref.bin ]; then
    LD_LIBRARY_PATH=$B taskset -c 0-2,6-8 $B/llama-perplexity "${base[@]}" --kl-divergence-base $G/kld.ref.bin > $G/kld.ref.log 2>&1
    LD_LIBRARY_PATH=$B taskset -c 0-2,6-8 $B/llama-perplexity "${base[@]}" --kl-divergence-base $G/kld.ref.bin --kl-divergence > $G/kld.off.log 2>&1
fi
env LD_LIBRARY_PATH=$B "$@" taskset -c 0-2,6-8 $B/llama-perplexity "${base[@]}" --kl-divergence-base $G/kld.ref.bin --kl-divergence > $G/kld.$label.log 2>&1
grep -E "^Mean +KLD|^Same top|^99.9%|Final estimate|^Mean PPL" $G/kld.$label.log
