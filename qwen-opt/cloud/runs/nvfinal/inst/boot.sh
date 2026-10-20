#!/usr/bin/env bash
# ON the instance (nvidia/cuda:12.8.1-runtime-ubuntu24.04): boot.sh qwen|uncensored — deps, prebuilt binaries, the
# model, hw snapshot, then fin.sh (correctness gate + ABBA before/after table).
set -uo pipefail
model=$1; H=/root/cloud
gpu=3090; [ "$model" = saluki ] && gpu=3060
RES=/root/results/nv-final-$gpu-$model-$(date +%Y%m%d)
mkdir -p "$RES/hw" "$RES/build" "$RES/logs" "$RES/gate" /root/models /root/bin
ln -sfn "$RES" /root/results/current
export DEBIAN_FRONTEND=noninteractive
# libgomp1: the runtime image lacks it and every llama.cpp binary needs it (nv24e lesson)
apt-get update -qq && apt-get install -y -qq --no-install-recommends curl ca-certificates jq python3 aria2 bc rsync zstd procps libgomp1 > /dev/null
for p in upstream topka2; do mkdir -p /root/bin/$p && tar -C /root/bin/$p --zstd -xf $H/$p.tar.zst; done
dl() {  # url file sha
    aria2c -q -x 8 -s 8 -c --file-allocation=none --checksum="sha-256=$3" -d /root/models -o "$2" "$1" \
        && touch "/root/models/$2.ok"
    echo "$2 $(date +%T) ok=$([ -f /root/models/$2.ok ] && echo yes || echo no)" >> "$RES/build/downloads.txt"
}
echo "downloads start $(date +%T)" >> "$RES/build/downloads.txt"
case $model in
    qwen|qwen60k) dl https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/resolve/4ca720788d1e01f1bff70c033e0d0028fd02e502/Qwen3.8-27B-UD-Q4_K_XL.gguf \
             Qwen3.8-27B-UD-Q4_K_XL.gguf 3f227079003add2511437e5b1e94812e363385225bf6a9b47b0054a72bc8b01e & ;;
    # orcarouter HF repo is gated; the Ollama registry blob is the same file (sha256 = the local ~/models/orca copy)
    uncensored) dl https://registry.ollama.ai/v2/orcarouter/qwen3.8-27b-uncensored/blobs/sha256:3445102e9cde5d562508642c100a2f5ac3368a5a3f748442811d7a95daee3bec \
             Qwen3.8-27B-Uncensored-Q4_K_M.gguf 3445102e9cde5d562508642c100a2f5ac3368a5a3f748442811d7a95daee3bec & ;;
    # 16e S1: Saluki IQ2-mix with the Kujira MTP graft (Qwen MTP head in Q8_0)
    saluki) dl https://huggingface.co/Kujira/Underdog-Saluki-27B-1.0-MTP-GGUF/resolve/5d92db9b7aa466a7c8f55e26dac2e366c36e8e5b/Underdog-Saluki-27B-1.0-IQ2-mix-MTP.gguf \
             Underdog-Saluki-27B-1.0-IQ2-mix-MTP.gguf 98f6ebb527917a2541df8e667d51c3ec8a8bb135b44c606d40cc6ed924e89e52 & ;;
    *) echo "unknown model $model"; exit 2 ;;
esac
nvidia-smi -q > "$RES/hw/nvidia-smi-q.txt"
{ uname -a; lscpu; free -g; df -h /root; cat /root/qwenbench-label; nproc; } > "$RES/hw/system.txt" 2>&1
for p in upstream topka2; do
    /root/bin/$p/llama-server --version > "$RES/build/version-$p.txt" 2>&1
    cp /root/bin/$p/HEAD.txt "$RES/build/HEAD-$p.txt"
done
case $model in
    saluki) exec bash $H/fin3060.sh ;;
    qwen60k) exec bash $H/fin60k.sh ;;   # run 2: the ~60k context at ctx 131072 (run 1 T OOM at 204800)
    *) exec bash $H/fin.sh "$model" ;;
esac
