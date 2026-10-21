#!/usr/bin/env bash
# GDN chunked MMA gate on the 3090: the kernel is opt-in (GGML_CUDA_GDN_MMA=1). It must leave PPL unchanged
# before its prefill gain counts. Everything runs interleaved 0-1-1-0 to survive host drift.
set -u
B=/root/w/fork/build/bin
M=/root/models/OrcaCyber-Nano-1.0-AI-Defense-Mix-15.7G.gguf
VOCAB=/root/cloud/draft_vocab_qwen38.txt
RES=/root/results/$(date +%Y%m%d-%H%M)/gdn-gate
mkdir -p "$RES"/{logs,lb}
export LD_LIBRARY_PATH=$B
if [ ! -f /root/.orca-cache-warm ]; then dd if="$M" of=/dev/null bs=8M status=none && touch /root/.orca-cache-warm; fi

echo "$(date -u +%T) gdn gate start -> $RES"

# 1. PPL: the gate. Identical values for =0 and =1 required.
for r in 0 1 1 0; do
    printf 'ppl gdn=%-2s ' "$r"
    GGML_CUDA_GDN_MMA=$r timeout 120 $B/llama-perplexity -m "$M" -f /root/cloud/corpus.txt -c 4096 -ngl 999 -fa on \
        -ctk q4_0 -ctv q4_0 --chunks 3 2>&1 | grep -oE "\[[0-9]+\][0-9.]+|nan" | tr '\n' ' '
    echo
done

# 2. prefill: only meaningful if the PPL gate passed
for r in 0 1 1 0; do
    printf 'pp2048 gdn=%-2s ' "$r"
    GGML_CUDA_GDN_MMA=$r $B/llama-bench -m "$M" -p 2048 -n 0 -r 3 -fa on -ctk q4_0 -ctv q4_0 -ngl 999 -o jsonl \
        2>/dev/null | python3 -c "import sys,json;print('%.0f t/s' % json.loads(sys.stdin.readline())['avg_ts'])"
done

# 3. greedy md5 with the production spec config, to see whether the MMA path changes the text
pkill -9 -f "llama[-]server.*--port 18442" 2>/dev/null; sleep 2
for r in 0 1; do
    env LLAMA_SPEC_LOOKUP=3 LLAMA_GPU_VERIFY=1 LLAMA_SPEC_COUPLED=1 LLAMA_CKPT_VRAM=2 LLAMA_CHAT_NATIVE=0 \
        LLAMA_SERVER_SAFE_SPECIAL=1 LLAMA_SERVER_SAFE_TOOLS=1 GGML_CUDA_KVQ=1 GGML_CUDA_GDN_MMA=$r \
        $B/llama-server --host 127.0.0.1 --port 18442 --no-webui -m "$M" -fa on -ctk q4_0 -ctv q4_0 -c 8192 \
        -np 1 -ngl 999 -fit off --jinja --spec-type draft-mtp --spec-draft-n-max 2 -ctkd q4_0 -ctvd q4_0 \
        --spec-draft-vocab "$VOCAB" --spec-draft-vocab-n 65536 --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs \
        > "$RES/logs/md5.gdn$r.log" 2>&1 &
    for _ in $(seq 200); do curl -sf http://127.0.0.1:18442/health >/dev/null 2>&1 && break; sleep 1; done
    printf 'md5 gdn=%-2s ' "$r"
    python3 /root/cloud/orca_measure.py md5 --port 18442 --label "gdn$r" --out "$RES/logs/md5.gdn$r.txt"
    pkill -9 -f "llama[-]server.*--port 18442" 2>/dev/null; sleep 2
done
echo "$(date -u +%T) gdn gate done"
