#!/usr/bin/env bash
# K-118 / K-116a / K-127 part 3, after run.sh + run2.sh on the same box (/root/fork, /root/m.gguf, /root/res).
#   1) K-116a: verify cost V(n) for n = 1, 2, 3, 5 with UPSTREAM b12110 llama-bench (the fork archive has none; the
#      fork's MMVQ is upstream's on NVIDIA): -p 1,2,3,5 -ub 5 -n 0, plus tg128, KV q4_0, FA on, -r 5.
#   2) K-127: the other fork variant (kvqleana if the host has AVX2, else skipped) on the same n4 arm as run.sh
#      (bench.py short, T=0 and T=1), compared with run.sh's n4-a / n4-b; start time to /health logged per arm.
#   3) K-118 long arm (cards with >= 15 GB): ctx 139264, one ~128k-token cold prompt then 256 tokens, plain and MTP n2.
# ON the box, detached: setsid nohup bash /root/k114/run3.sh > /dev/null 2>&1 < /dev/null &   marker /root/res/DONE3
set -uo pipefail
R=/root/res; F=/root/fork; M=/root/m.gguf; U=/root/up
exec >> "$R/run3.log" 2>&1
ph() { echo "$(date +%s) $*" | tee -a "$R/phases.txt"; }
B=$(dirname "$(find "$F/x" -name llama-server -type f | head -1)")
pgrep -f "query-gpu=timestamp" > /dev/null || (nvidia-smi --query-gpu=timestamp,power.draw,power.limit,temperature.gpu,clocks.sm,clocks.mem,utilization.gpu,memory.used --format=csv,noheader -l 1 >> "$R/smi.csv") &
SMI=$!
stop() { kill -TERM "$1"; for _ in $(seq 60); do kill -0 "$1" 2> /dev/null || break; sleep 1; done; kill -KILL "$1" 2> /dev/null; wait "$1" 2> /dev/null; }
up() {  # wait for /health of pid $1, echo seconds
    local t0=$SECONDS
    for _ in $(seq 1200); do curl -fs localhost:8090/health > /dev/null && break; kill -0 "$1" 2> /dev/null || break; sleep 1; done
    echo $((SECONDS - t0))
}

# 1) upstream llama-bench
mkdir -p "$U/x"
curl -fsSL --retry 5 -o "$U/up.tar.gz" https://github.com/ggml-org/llama.cpp/releases/download/b12110/llama-b12110-bin-ubuntu-cuda-12.8-x64.tar.gz \
    && tar -C "$U/x" -xzf "$U/up.tar.gz" && tar -C "$U/x" -xzf "$F/cudart.tar.gz"
UB=$(dirname "$(find "$U/x" -name llama-bench -type f | head -1)")
if [ -x "$UB/llama-bench" ]; then
    find "$U/x" -name '*.so*' \( -type f -o -type l \) -not -path "$UB/*" -exec cp -an {} "$UB/" \;
    UBENCH=(-m "$M" -ngl 999 -fa 1 -ctk q4_0 -ctv q4_0 -r 5 -o jsonl)
    LD_LIBRARY_PATH=$UB timeout 400 "$UB/llama-bench" "${UBENCH[@]}" -p 1,2,3,5 -ub 5 -b 5 -n 0 > "$R/up-vn.jsonl" 2> "$R/logs/up-vn.err"
    LD_LIBRARY_PATH=$UB timeout 300 "$UB/llama-bench" "${UBENCH[@]}" -p 0 -n 128 > "$R/up-tg.jsonl" 2> "$R/logs/up-tg.err"
    ph "upstream V(n) + tg128"
else ph "upstream llama-bench missing"; fi

SPEC=(--spec-draft-vocab "$F/vocab.txt" --spec-draft-vocab-n 65536 --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs -ctkd q4_0 -ctvd q4_0)
srv() {  # bindir label ctx n_max(0 = plain) -> pid
    local extra=(); [ "$4" -gt 0 ] && extra=(--spec-type draft-mtp --spec-draft-n-max "$4" "${SPEC[@]}")
    env LD_LIBRARY_PATH="$1" GGML_CUDA_KVQ=1 LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_GPU_VERIFY=1 LLAMA_SERVER_CACHE_SHARE_MIN=1024 \
        "$1/llama-server" -m "$M" -c "$3" -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -ub 256 -np 1 --jinja --alias k114 "${extra[@]}" \
        --host 127.0.0.1 --port 8090 --no-webui > "$R/logs/server-$2.log" 2>&1 < /dev/null &
    echo $!
}

# 2) K-127: the non-AVX2 build on an AVX2 host (run.sh used kvqlean there)
if [ "$(cat "$R/variant.txt")" = kvqlean ]; then
    F2=/root/fork2; mkdir -p "$F2/x"
    curl -fsSL --retry 5 -o "$F2/fork.tar.gz" https://github.com/jarojarojaro-jaro/KERNEL/releases/download/enigma-engines-cuda-2026-11-07/llama-kvqleana-bin-ubuntu-cuda-12.8-x64.tar.gz \
        && tar -C "$F2/x" -xzf "$F2/fork.tar.gz" && tar -C "$F2/x" -xzf "$F/cudart.tar.gz"
    B2=$(dirname "$(find "$F2/x" -name llama-server -type f | head -1)")
    find "$F2/x" -name '*.so*' \( -type f -o -type l \) -not -path "$B2/*" -exec cp -an {} "$B2/" \;
    pid=$(srv "$B2" n4-noavx2 8192 4); echo "n4-noavx2 $(up "$pid")" >> "$R/start_s.txt"
    TOKENIZE_PORT=8090 timeout 900 python3 /root/k114/bench.py n4-noavx2 8090 k114 short > "$R/logs/n4-noavx2.bench.log" 2>&1
    stop "$pid"; ph "arm n4-noavx2"
    pid=$(srv "$B" n4-c 8192 4); echo "n4-c $(up "$pid")" >> "$R/start_s.txt"
    TOKENIZE_PORT=8090 timeout 900 python3 /root/k114/bench.py n4-c 8090 k114 short > "$R/logs/n4-c.bench.log" 2>&1
    stop "$pid"; ph "arm n4-c"
else ph "K-127 skipped: host without AVX2"; fi

# 3) long arm on >= 15 GB cards
vram=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
if [ "${vram:-0}" -ge 15000 ]; then
    for a in plain:0 n2:2; do
        pid=$(srv "$B" "long-${a%%:*}" 139264 "${a##*:}"); echo "long-${a%%:*} $(up "$pid")" >> "$R/start_s.txt"
        timeout 900 python3 /root/k114/lp.py 8090 "${a%%:*}" > "$R/logs/long-${a%%:*}.log" 2>&1
        nvidia-smi --query-gpu=memory.used --format=csv,noheader > "$R/logs/long-${a%%:*}.vram"
        stop "$pid"; ph "long ${a%%:*}"
    done
else ph "long arm skipped: ${vram} MiB"; fi
kill $SMI 2> /dev/null; ph done3; touch "$R/DONE3"
