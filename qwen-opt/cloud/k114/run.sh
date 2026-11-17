#!/usr/bin/env bash
# K-112 + K-114 on one rented NVIDIA card (3090 / 5060 Ti / 3060): same model on every card (Qwen3.8-27B GSQ-RCO
# IQ3_XXS-mtp, 10.44 GB, fits 12 GB at ctx 16k) + published Enigma CUDA fork (kvqlean, kvqleana without AVX2).
# Measures: host power/clock limit, plain decode tg128 (target pass ms), verify cost pp5 ub5, prefill pp4096/pp16384,
# MTP step at n4 and n2, T=0 and T=1, GPU_VERIFY 1 (fork default). One server at a time, one SIGTERM then 60 s.
# ON the box, detached:  setsid nohup bash /root/k114/run.sh > /dev/null 2>&1 < /dev/null &   done marker /root/res/DONE
# Needs /root/k114/bench.py (= qwen-opt/cloud/nv69q/bench.py, "short" block only, no corpus needed).
set -uo pipefail
R=/root/res; F=/root/fork; M=/root/m.gguf; mkdir -p "$R/logs" "$F"; exec > "$R/run.log" 2>&1
ph() { echo "$(date +%s) $*" | tee -a "$R/phases.txt"; }
dl() { for t in 1 2 3; do curl -fsSL --retry 5 -o "$2" "$1" && [ "$(stat -c %s "$2")" = "$3" ] && return 0; sleep 5; done; return 1; }
ph start
nvidia-smi --query-gpu=name,memory.total,driver_version,power.limit,power.default_limit,clocks.max.sm,clocks.max.mem,pcie.link.gen.current,pcie.link.width.current --format=csv > "$R/gpu.csv"
nvidia-smi -q -d POWER,CLOCK > "$R/power.txt"; nproc > "$R/nproc.txt"
grep -q -w avx2 /proc/cpuinfo && V=kvqlean || V=kvqleana; echo "$V" > "$R/variant.txt"
(nvidia-smi --query-gpu=timestamp,power.draw,power.limit,temperature.gpu,clocks.sm,clocks.mem,utilization.gpu,memory.used --format=csv,noheader -l 1 > "$R/smi.csv") &
SMI=$!
apt-get update -qq > /dev/null 2>&1; DEBIAN_FRONTEND=noninteractive apt-get install -y -qq curl python3 ca-certificates > "$R/apt.log" 2>&1
REL=https://github.com/jarojarojaro-jaro/KERNEL/releases/download/enigma-engines-cuda-2026-11-07
dl https://huggingface.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF/resolve/main/Qwen3.8-27B-GSQ-RCO-IQ3_XXS-mtp.gguf "$M" 10442827840 &
DL=$!
curl -fsSL --retry 5 -o "$F/fork.tar.gz" "$REL/llama-$V-bin-ubuntu-cuda-12.8-x64.tar.gz"
curl -fsSL --retry 5 -o "$F/cudart.tar.gz" https://github.com/ggml-org/llama.cpp/releases/download/b12110/cudart-llama-b12110-bin-ubuntu-cuda-12.8-x64.tar.gz
dl "$REL/draft_vocab_qwen38.txt" "$F/vocab.txt" 1627130
(cd "$F" && sha256sum fork.tar.gz cudart.tar.gz vocab.txt) > "$R/sha256.txt"
mkdir -p "$F/x" && tar -C "$F/x" -xzf "$F/fork.tar.gz" && tar -C "$F/x" -xzf "$F/cudart.tar.gz"
B=$(dirname "$(find "$F/x" -name llama-server -type f | head -1)")
find "$F/x" -name '*.so*' \( -type f -o -type l \) -not -path "$B/*" -exec cp -an {} "$B/" \;
export LD_LIBRARY_PATH=$B
"$B/llama-server" --version > "$R/version.txt" 2>&1
wait $DL || { ph "model download failed"; kill $SMI; touch "$R/DONE"; exit 1; }
ph "ready variant=$V"

# 1) llama-bench: plain decode (target pass), verify-sized batch, prefill
BENCH=(-m "$M" -ngl 999 -fa 1 -ctk q4_0 -ctv q4_0 -r 3 -o jsonl)
[ -x "$B/llama-bench" ] && {
    timeout 300 "$B/llama-bench" "${BENCH[@]}" -p 0 -n 128 > "$R/bench-tg.jsonl" 2> "$R/logs/bench-tg.err"; ph "bench tg128"
    timeout 300 "$B/llama-bench" "${BENCH[@]}" -p 5 -n 0 -ub 5 -b 5 > "$R/bench-pp5.jsonl" 2> "$R/logs/bench-pp5.err"; ph "bench pp5"
    timeout 600 "$B/llama-bench" "${BENCH[@]}" -p 4096,16384 -n 0 -ub 512 > "$R/bench-pp.jsonl" 2> "$R/logs/bench-pp.err"; ph "bench pp"
} || ph "no llama-bench in archive"

# 2) server: MTP n4 and n2, T=0/T=1 (bench.py "short" runs both temperatures, 6 prompts)
arm() {  # label n_max
    env GGML_CUDA_KVQ=1 LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_GPU_VERIFY=1 LLAMA_SERVER_CACHE_SHARE_MIN=1024 \
        "$B/llama-server" -m "$M" -c 16384 -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -ub 256 -np 1 --jinja --alias k114 \
        --spec-type draft-mtp --spec-draft-n-max "$2" -ctkd q4_0 -ctvd q4_0 --spec-draft-vocab "$F/vocab.txt" \
        --spec-draft-vocab-n 65536 --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs \
        --host 127.0.0.1 --port 8090 --no-webui > "$R/logs/server-$1.log" 2>&1 < /dev/null &
    local pid=$!
    for _ in $(seq 600); do curl -fs localhost:8090/health > /dev/null && break; kill -0 $pid 2> /dev/null || break; sleep 1; done
    nvidia-smi --query-gpu=memory.used --format=csv,noheader > "$R/logs/$1.vram"
    TOKENIZE_PORT=8090 timeout 900 python3 /root/k114/bench.py "$1" 8090 k114 short > "$R/logs/$1.bench.log" 2>&1
    kill -TERM $pid; for _ in $(seq 60); do kill -0 $pid 2> /dev/null || break; sleep 1; done; kill -KILL $pid 2> /dev/null
    wait $pid 2> /dev/null; ph "arm $1"
}
arm n4-a 4; arm n2 2; arm n4-b 4
kill $SMI; ph done; touch "$R/DONE"
