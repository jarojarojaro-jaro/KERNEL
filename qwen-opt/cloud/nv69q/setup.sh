#!/usr/bin/env bash
# R69b Q1 on a rented RTX 3090: qwen-warp v0.8.0 (689901c) vs our enigma-cuda-fork (published kvqleana asset).
# ON the box (nvidia/cuda:13.0.2-devel-ubuntu24.04). Downloads run in parallel with the qwen-warp build.
# Writes /root/res/{hw,setup.log,*.done}.
set -uo pipefail
RES=/root/res; M=/root/models; F=/root/fork
mkdir -p "$RES/hw" "$M/swift" "$F"
log() { echo "=== $(date +%T) $*"; }

# ---- host facts: foreign GPU processes, power limit, CPU flags -------------------------------------------------------
nvidia-smi > "$RES/hw/nvidia-smi.txt" 2>&1
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv > "$RES/hw/gpu-procs.csv" 2>&1
nvidia-smi -q -d POWER > "$RES/hw/power.txt" 2>&1
nvidia-smi --query-gpu=name,memory.total,memory.used,driver_version,pcie.link.gen.max,pcie.link.width.max,power.limit,power.default_limit,clocks.max.sm --format=csv > "$RES/hw/gpu.csv" 2>&1
lscpu > "$RES/hw/lscpu.txt"; grep -o -w -E 'avx2|avx512f|fma|f16c|avx' /proc/cpuinfo | sort | uniq -c > "$RES/hw/cpuflags.txt"
free -g > "$RES/hw/free.txt"; df -h /root > "$RES/hw/df.txt"; cat /sys/fs/cgroup/cpu.max > "$RES/hw/cpu.max" 2>/dev/null
log "hw recorded"

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq && apt-get install -y -qq --no-install-recommends python3 python3.12 python3.12-dev build-essential ca-certificates \
    curl git > "$RES/apt.log" 2>&1
log "apt done"

# ---- downloads (background) -------------------------------------------------------------------------------------------
dl() {  # url dest size
    for t in 1 2 3; do
        curl -fsSL --retry 5 -o "$2" "$1" && [ "$(stat -c %s "$2")" = "$3" ] && return 0
        echo "retry $t $2"; sleep 5
    done; return 1
}
(
    HF=https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27b-INT4/resolve/81a28ee75eb1cd469f209813a368a79a7e3db3bc
    for f in QUANTIZATION_MANIFEST.json chat_template.jinja config.json generation_config.json model.safetensors.index.json \
             processor_config.json recipe.yaml tokenizer.json tokenizer_config.json LICENSE NOTICE; do
        curl -fsSL --retry 5 -o "$M/swift/$f" "$HF/$f" || echo "FAIL $f"
    done
    dl "$HF/model-00001-of-00005.safetensors" "$M/swift/model-00001-of-00005.safetensors" 3969055792 &
    dl "$HF/model-00002-of-00005.safetensors" "$M/swift/model-00002-of-00005.safetensors" 3982295724 &
    dl "$HF/model-00003-of-00005.safetensors" "$M/swift/model-00003-of-00005.safetensors" 3981907304 &
    wait
    dl "$HF/model-00004-of-00005.safetensors" "$M/swift/model-00004-of-00005.safetensors" 3990818108 &
    dl "$HF/model-00005-of-00005.safetensors" "$M/swift/model-00005-of-00005.safetensors" 2679307784 &
    dl "$HF/model_mtp.safetensors" "$M/swift/model_mtp.safetensors" 849400392 &
    wait
    du -sb "$M/swift" > "$RES/swift.done"; log "swift downloaded"
) > "$RES/dl-swift.log" 2>&1 &
(
    dl https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/resolve/main/Qwen3.8-27B-UD-Q4_K_XL.gguf "$M/Qwen3.8-27B-UD-Q4_K_XL.gguf" 17559178144 \
        && sha256sum "$M/Qwen3.8-27B-UD-Q4_K_XL.gguf" > "$RES/gguf.done"; log "gguf downloaded"
) > "$RES/dl-gguf.log" 2>&1 &
(
    R=https://github.com/jarojarojaro-jaro/KERNEL/releases/download/enigma-engines-cuda-2026-11-07
    dl "$R/llama-kvqleana-bin-ubuntu-cuda-12.8-x64.tar.gz" "$F/kvqleana.tar.gz" 130083180
    dl https://github.com/ggml-org/llama.cpp/releases/download/b12110/cudart-llama-b12110-bin-ubuntu-cuda-12.8-x64.tar.gz "$F/cudart.tar.gz" 594371477
    dl "$R/draft_vocab_qwen38.txt" "$F/draft_vocab_qwen38.txt" 1627130
    (cd "$F" && sha256sum kvqleana.tar.gz cudart.tar.gz draft_vocab_qwen38.txt) > "$RES/hw/fork-sha256.txt"
    mkdir -p "$F/x" && tar -C "$F/x" -xzf "$F/kvqleana.tar.gz" && tar -C "$F/x" -xzf "$F/cudart.tar.gz"
    bin=$(dirname "$(find "$F/x" -name llama-server -type f | head -1)")
    find "$F/x" -name '*.so*' \( -type f -o -type l \) -not -path "$bin/*" -exec cp -an {} "$bin/" \;
    echo "$bin" > "$F/.bindir"
    LD_LIBRARY_PATH=$bin "$bin/llama-server" --version > "$RES/hw/fork-version.txt" 2>&1
    LD_LIBRARY_PATH=$bin "$bin/llama-server" --list-devices >> "$RES/hw/fork-version.txt" 2>&1
    touch "$RES/fork.done"; log "fork installed"
) > "$RES/dl-fork.log" 2>&1 &

# ---- qwen-warp: uv env + engine build ---------------------------------------------------------------------------------
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh > "$RES/uv-install.log" 2>&1
cd /root && git clone -q https://github.com/tuan3w/qwen-warp && cd qwen-warp && git checkout -q 689901c
git log --oneline -1 > "$RES/hw/warp-commit.txt"
export UV_PYTHON=/usr/bin/python3.12 UV_LINK_MODE=hardlink UV_CACHE_DIR=/root/.cache/uv
log "uv sync start"
uv sync --frozen --group dev > "$RES/uv-sync.log" 2>&1 || { log "uv sync FAILED"; tail -20 "$RES/uv-sync.log"; }
log "uv sync done"
nvcc --version > "$RES/hw/nvcc.txt" 2>&1
make -C engine -j"$(nproc)" > "$RES/warp-build.log" 2>&1 && touch "$RES/warp.done" || { log "warp build FAILED"; tail -30 "$RES/warp-build.log"; }
log "warp engine built"
wait
log "setup complete"
