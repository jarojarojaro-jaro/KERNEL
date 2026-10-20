#!/usr/bin/env bash
# ON the instance (nvidia/cuda:12.8.1-devel-ubuntu24.04), nv-3090 round 2026-10-20: deps, prebuilt U/T binaries,
# model download, nsys, hw snapshot. Logs to /root/results/nv3090/.
set -uo pipefail
H=/root/cloud; RES=/root/results/nv3090
mkdir -p "$RES/hw" "$RES/build" "$RES/logs" "$RES/gate" /root/models /root/bin
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq && apt-get install -y -qq --no-install-recommends curl ca-certificates jq python3 aria2 bc rsync \
    zstd procps libgomp1 cmake ninja-build git ccache libssl-dev > /dev/null
for p in upstream topka2; do mkdir -p /root/bin/$p && tar -C /root/bin/$p --zstd -xf $H/$p.tar.zst; done
( false && aria2c -q -x 8 -s 8 -c --file-allocation=none \
    --checksum=sha-256=3f227079003add2511437e5b1e94812e363385225bf6a9b47b0054a72bc8b01e -d /root/models \
    -o Qwen3.8-27B-UD-Q4_K_XL.gguf \
    https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/resolve/4ca720788d1e01f1bff70c033e0d0028fd02e502/Qwen3.8-27B-UD-Q4_K_XL.gguf \
    && touch /root/models/Qwen3.8-27B-UD-Q4_K_XL.gguf.ok; echo "model $(date +%T)" >> "$RES/build/downloads.txt" ) &
apt-get install -y -qq --no-install-recommends cuda-nsight-systems-12-8 > "$RES/build/nsys-install.log" 2>&1 \
    || apt-get install -y -qq --no-install-recommends nsight-systems >> "$RES/build/nsys-install.log" 2>&1
nvidia-smi -q > "$RES/hw/nvidia-smi-q.txt"
{ uname -a; lscpu; free -g; df -h /root; nproc; } > "$RES/hw/system.txt" 2>&1
for p in upstream topka2; do cp /root/bin/$p/HEAD.txt "$RES/build/HEAD-$p.txt"; done
wait
echo "setup done $(date +%T)"
