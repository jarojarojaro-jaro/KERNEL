#!/usr/bin/env bash
# K-103 on a rented Vast RTX 5060 Ti: upstream llama.cpp b11856 (Enigma pin) vs v1.0.0 (b12359), sm_120 only.
# Host power limit is whatever the offer has (logged in power.txt). Runs detached on the instance: nohup setsid bash /root/k103/run.sh &  Results in /root/res, done marker /root/res/DONE.
set -uo pipefail
R=/root/res; mkdir -p "$R/logs"; exec > "$R/run.log" 2>&1
cd /root/k103
ph() { echo "$(date +%s) $*" | tee -a "$R/phases.txt"; }
M=/root/m.gguf; SZ=10442827840
URL=https://huggingface.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF/resolve/main/Qwen3.8-27B-GSQ-RCO-IQ3_XXS-mtp.gguf
ph start
nvidia-smi -q -d POWER,CLOCK > "$R/power.txt"; nvidia-smi > "$R/smi0.txt"; nproc > "$R/nproc.txt"
(nvidia-smi --query-gpu=timestamp,temperature.gpu,power.draw,memory.used,clocks.sm --format=csv -l 2 > "$R/smi.csv") &
curl -sSL --retry 3 -o "$M" "$URL" > "$R/dl.log" 2>&1 & DL=$!
(apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq git cmake python3 libssl-dev) > "$R/apt.log" 2>&1
ph apt
for t in b11856 v1.0.0; do
    git clone -q --depth 1 --branch "$t" https://github.com/ggml-org/llama.cpp "/root/$t" && git -C "/root/$t" log -1 --format="$t %H %cd" >> "$R/commits.txt"
    cmake -S "/root/$t" -B "/root/$t/build" -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=120 -DCMAKE_BUILD_TYPE=Release \
        -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF > "$R/logs/cmake-$t.log" 2>&1
    cmake --build "/root/$t/build" --target llama-server llama-bench -j"$(nproc)" > "$R/logs/build-$t.log" 2>&1
    ph "built $t rc=$?"
done
wait $DL; ph "dl rc=$? size=$(stat -c %s $M)"
[ "$(stat -c %s $M)" = $SZ ] || { ph "model size mismatch"; touch "$R/DONE"; exit 1; }

PORT=8090
arm() {  # arm <label> <tag> <extra server args...>
    local lab=$1 t=$2; shift 2
    "/root/$t/build/bin/llama-server" -m "$M" -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c 65536 -ub 256 --jinja \
        --port $PORT "$@" > "$R/logs/server-$lab.log" 2>&1 & local pid=$!
    for _ in $(seq 150); do curl -sf localhost:$PORT/health > /dev/null && break; sleep 2; done
    echo "$lab load_vram_MiB $(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)" >> "$R/vram.txt"
    timeout 600 python3 spec_sweep.py --label "$lab" --port $PORT --temps 1.0 --seeds 1 >> "$R/sweep.txt" 2>&1
    echo "$lab peak_vram_MiB $(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)" >> "$R/vram.txt"
    kill -TERM $pid; for _ in $(seq 60); do kill -0 $pid 2>/dev/null || break; sleep 1; done; kill -KILL $pid 2>/dev/null
    wait $pid 2>/dev/null; ph "arm $lab"
}
MTP=(--spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-n-ubatch 64)
arm A1-b11856-mtp2 b11856 "${MTP[@]}"
arm B1-v1.0.0-mtp2 v1.0.0 "${MTP[@]}"
arm B2-v1.0.0-mtp2 v1.0.0 "${MTP[@]}"
arm A2-b11856-mtp2 b11856 "${MTP[@]}"
for t in b11856 v1.0.0; do
    "/root/$t/build/bin/llama-bench" -m "$M" -ngl 999 -fa 1 -ctk q4_0 -ctv q4_0 -p 576 -n 0 -ub 4,8,16 -r 3 -o jsonl \
        > "$R/bench-$t.jsonl" 2> "$R/logs/bench-$t.err"; ph "bench $t"
done
cp spec_sweep.jsonl "$R/" 2>/dev/null
ph done; touch "$R/DONE"
