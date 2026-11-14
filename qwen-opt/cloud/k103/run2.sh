#!/usr/bin/env bash
# K-103 gate before moving the Enigma CUDA pin b11856 -> b12359 (= llama.cpp v1.0.0): official prebuilt release
# binaries (what Enigma downloads), RTX 5060 Ti, Qwen3.8-27B ISTA GSQ IQ3_XXS-mtp, KV q4_0.
#  1) KLD vs b11856 logits (wikitext-2 test, 20 x 512, plain): b11856 ub 256 / ub 8 = upstream's own batch-split noise;
#     b12359 ub 512 (same ub as the base) / ub 8 (few-row MMQ #31533 path). Gate: b12359 within b11856's noise.
#  2) MTP n 3 + ubd 64 (24/32 GB recipe), spec_sweep T=1 seed 1, A B B A at ctx 65536, ub 256.
# Runs detached: nohup setsid bash /root/k103/run2.sh &   Results /root/res2, marker /root/res2/DONE.
set -uo pipefail
R=/root/res2; mkdir -p "$R/logs"; exec > "$R/run.log" 2>&1
cd /root/k103
ph() { echo "$(date +%s) $*" | tee -a "$R/phases.txt"; }
M=/root/m.gguf; SZ=10442827840
URL=https://huggingface.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF/resolve/main/Qwen3.8-27B-GSQ-RCO-IQ3_XXS-mtp.gguf
GH=https://github.com/ggml-org/llama.cpp/releases/download
ph start
nvidia-smi -q -d POWER > "$R/power.txt"
curl -sSL --retry 3 -o "$M" "$URL" > "$R/dl.log" 2>&1 & DL=$!
for t in b11856 b12359; do
    mkdir -p "/root/$t" && curl -sSL --retry 3 "$GH/$t/llama-$t-bin-ubuntu-cuda-12.8-x64.tar.gz" | tar xz -C "/root/$t"
    B=$(dirname "$(find "/root/$t" -name llama-server -type f | head -1)"); echo "$t $B" >> "$R/bins.txt"
    "$B/llama-server" --version >> "$R/bins.txt" 2>&1
done
curl -sSL --retry 3 -o /root/wt.zip https://huggingface.co/datasets/ggml-org/ci/resolve/main/wikitext-2-raw-v1.zip \
    && (cd /root && python3 -c "import zipfile; zipfile.ZipFile('/root/wt.zip').extractall('/root')")
W=$(find /root -name wiki.test.raw | head -1); ph "wiki $W"
wait $DL; ph "dl size=$(stat -c %s $M)"
[ "$(stat -c %s $M)" = $SZ ] || { ph "model size mismatch"; touch "$R/DONE"; exit 1; }
bin() { awk -v t="$1" '$1 == t { print $2 }' "$R/bins.txt"; }
ppl() {  # ppl <label> <tag> <ub> [base]
    local lab=$1 t=$2 ub=$3 mode=$4
    "$(bin $t)/llama-perplexity" -m "$M" -f "$W" -c 512 --chunks 20 -ngl 999 -fa on -b 512 -ub "$ub" \
        $mode > "$R/logs/ppl-$lab.log" 2>&1
    ph "ppl $lab rc=$?"
}
ppl base b11856 512 "--kl-divergence-base /root/base.kld"
for a in "a256 b11856 256" "a8 b11856 8" "b512 b12359 512" "b8 b12359 8"; do
    set -- $a; ppl "$1" "$2" "$3" "--kl-divergence-base /root/base.kld --kl-divergence"
done
PORT=8090
arm() {  # arm <label> <tag>
    local lab=$1 t=$2
    "$(bin $t)/llama-server" -m "$M" -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c 65536 -ub 256 --jinja --port $PORT \
        --spec-type draft-mtp --spec-draft-n-max 3 --spec-draft-n-ubatch 64 > "$R/logs/server-$lab.log" 2>&1 & local pid=$!
    for _ in $(seq 150); do curl -sf localhost:$PORT/health > /dev/null && break; sleep 2; done
    timeout 600 python3 spec_sweep.py --label "$lab" --port $PORT --temps 1.0 --seeds 1 >> "$R/sweep.txt" 2>&1
    kill -TERM $pid; for _ in $(seq 60); do kill -0 $pid 2>/dev/null || break; sleep 1; done; kill -KILL $pid 2>/dev/null
    wait $pid 2>/dev/null; ph "arm $lab"
}
arm A1-b11856-mtp3 b11856; arm B1-b12359-mtp3 b12359; arm B2-b12359-mtp3 b12359; arm A2-b11856-mtp3 b11856
cp spec_sweep.jsonl "$R/" 2>/dev/null
for l in a256 a8 b512 b8; do echo "$l $(grep -E 'Mean +KLD|Same top p' "$R/logs/ppl-$l.log" | tr -s ' ' | tr '\n' ' ')"; done > "$R/kld.txt"
ph done; touch "$R/DONE"
