#!/usr/bin/env bash
# Inkling 2 Mini on a rented NVIDIA card (owner 2026-11-21 03:04: "można też zrobić testy na 3090 na Vaście").
# Builds llama.cpp PR #32695 (6196d98, looped Inkling 2) for this GPU, downloads AtomicChat Inkling-2-Mini-Uncensored-AD-Q4_K
# (16.53 GB) + unsloth DSpark Q8_0 drafter, then: llama-bench tg128 / pp512 / pp5 (verify-sized), server without and with
# DSpark (xbench: copy tasks T=0, story T=0.7, long 2k/8k). Results /root/res, FINISHED by the launcher chain.
set -uo pipefail
R=/root/res; W=/root/w; mkdir -p "$R/logs" "$W"; exec > "$R/run.log" 2>&1
ph() { echo "$(date +%s) $*" | tee -a "$R/phases.txt"; }
ph start
nvidia-smi --query-gpu=name,memory.total,driver_version,power.limit,power.default_limit,clocks.max.sm,clocks.max.mem --format=csv > "$R/gpu.csv"
nproc > "$R/nproc.txt"
(nvidia-smi --query-gpu=timestamp,power.draw,power.limit,temperature.gpu,clocks.sm,clocks.mem,utilization.gpu,memory.used --format=csv,noheader -l 1 > "$R/smi.csv") &
SMI=$!
M=$W/ink.gguf; D=$W/dspark.gguf
HF=https://huggingface.co
bash /root/k114/pdl.sh $HF/AtomicChat/Inkling-2-Mini-Uncensored-GGUF/resolve/main/Inkling-2-Mini-Uncensored-AD-Q4_K.gguf "$M" 16525558464 16 > "$R/logs/dl.log" 2>&1 &
DL=$!
curl -fsSL --retry 5 -o "$D" $HF/unsloth/Inkling-2-Mini-GGUF/resolve/main/dspark-Inkling-2-Mini-Q8_0.gguf
apt-get update -qq > /dev/null 2>&1; DEBIAN_FRONTEND=noninteractive apt-get install -y -qq git cmake build-essential python3 curl ca-certificates libgomp1 > "$R/apt.log" 2>&1
git clone -q https://github.com/ggml-org/llama.cpp "$W/src" && cd "$W/src" && git fetch -q origin pull/32695/head:ink && git checkout -q ink
git log --oneline -1 > "$R/commit.txt"
CC=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -1 | tr -d .)
cmake -S . -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=$CC -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF > "$R/logs/cmake.log" 2>&1
cmake --build build -j"$(nproc)" --target llama-server llama-bench > "$R/logs/build.log" 2>&1 || { ph "build failed"; tail -30 "$R/logs/build.log" > "$R/build-tail.txt"; kill $SMI; exit 1; }
ph "built sm_$CC"
B=$W/src/build/bin
wait $DL || { ph "model download failed"; kill $SMI; exit 1; }
ls -la "$M" "$D" > "$R/files.txt"; ph ready
timeout 600 "$B/llama-bench" -m "$M" -ngl 99 -fa 1 -p 512,5 -n 128 -r 3 > "$R/bench.txt" 2> "$R/logs/bench.err"; ph bench
for arm in plain dspark; do
    extra=(); [ $arm = dspark ] && extra=(-md "$D" --spec-type draft-dspark)
    "$B/llama-server" -m "$M" "${extra[@]}" -ngl 99 -fa on -c 32768 --jinja --host 127.0.0.1 --port 8090 > "$R/logs/server-$arm.log" 2>&1 < /dev/null &
    pid=$!
    for _ in $(seq 600); do curl -fs localhost:8090/health > /dev/null && break; kill -0 $pid 2> /dev/null || break; sleep 1; done
    nvidia-smi --query-gpu=memory.used --format=csv,noheader > "$R/logs/$arm.vram"
    timeout 900 python3 /root/k114/xbench.py 8090 /root/k114 "ink-$arm" > "$R/xbench-$arm.txt" 2>&1
    kill -TERM $pid; for _ in $(seq 60); do kill -0 $pid 2> /dev/null || break; sleep 1; done; kill -KILL $pid 2> /dev/null
    ph "arm $arm"
done
kill $SMI; ph done
