#!/usr/bin/env bash
# ON the Vast host (ubuntu:24.04): deps, official llama.cpp CUDA 12.8 release binaries (the assets Enigma's
# data/engines.json pins), models from HF with sha256, hw snapshot; then nv67.py. Everything logs to /root/res.
#   setup.sh card.json
set -uo pipefail
CARD=$1
RES=$(python3 -c "import json;print(json.load(open('$CARD')).get('res','/root/res'))" 2>/dev/null || echo /root/res)
mkdir -p "$RES/hw" /root/eng /root/models /root/dl
export DEBIAN_FRONTEND=noninteractive
if ! command -v aria2c > /dev/null || ! command -v python3 > /dev/null; then
    apt-get update -qq && apt-get install -y -qq --no-install-recommends curl ca-certificates aria2 python3 jq libgomp1 \
        procps pciutils > "$RES/hw/apt.log" 2>&1
fi
echo "apt done $(date +%T)"
J() { python3 -c "import json,sys;d=json.load(open('$CARD'));print(eval(sys.argv[1]))" "$1"; }

# hardware snapshot (no addresses: nvidia-smi -q has none; lscpu/free/df only)
{ nvidia-smi --query-gpu=name,memory.total,driver_version,power.limit,power.default_limit,power.max_limit,clocks.max.sm,clocks.max.mem,pcie.link.gen.max,pcie.link.width.max,vbios_version --format=csv
  nvidia-smi | sed -n 1,4p | grep -o 'CUDA Version: [0-9.]*'
  lscpu | grep -E 'Model name|^CPU\(s\)|Thread|Socket|NUMA node\(s\)'
  free -g | sed -n 1,2p; nproc; cat /sys/fs/cgroup/cpu.max 2>/dev/null; cat /sys/fs/cgroup/memory.max 2>/dev/null
  df -h /root | tail -1; uname -r; } > "$RES/hw/system.txt" 2>&1
nvidia-smi -q > "$RES/hw/nvidia-smi-q.txt" 2>&1

dl_model() {  # url file sha
    [ -f "/root/models/$2.ok" ] && return 0
    aria2c -q -x 8 -s 8 -c --file-allocation=none --checksum="sha-256=$3" -d /root/models -o "$2" "$1" \
        && touch "/root/models/$2.ok"
    echo "$2 $(date +%T) ok=$([ -f "/root/models/$2.ok" ] && echo yes || echo no)" >> "$RES/hw/downloads.txt"
}
eng() {  # tag
    local t=$1 d=/root/eng/$1 a
    [ -f "$d/.bindir" ] && return 0
    mkdir -p "$d"
    # our own builds (b12110lean, topka2) come as /root/nv/llama-<tag>-bin-ubuntu-cuda-12.8-x64.tar.gz and reuse the
    # cudart/cublas of the official base engine (card "engine_base": {tag: base}); official tags download from GitHub
    local own=/root/nv/llama-$t-bin-ubuntu-cuda-12.8-x64.tar.gz bt
    bt=$(J "d.get('engine_base', {}).get('$t', '$t')")
    if [ -f "$own" ]; then
        local base=/root/eng/$bt
        for _ in $(seq 180); do [ -f "$base/.bindir" ] && break; sleep 10; done
        tar -C "$d" -xzf "$own" || { echo "engine $t: bad tarball"; return 1; }
        sha256sum "$own" >> "$RES/hw/engine-sha256.txt"
        local b2; b2=$(dirname "$(find "$d" -name llama-server -type f | head -1)")
        cp -an "$(cat "$base/.bindir")"/libcu* "$b2/"
    else
        for a in "llama-$t-bin-ubuntu-cuda-12.8-x64.tar.gz" "cudart-llama-$t-bin-ubuntu-cuda-12.8-x64.tar.gz"; do
            curl -fsSL --retry 3 -o "/root/dl/$a" "https://github.com/ggml-org/llama.cpp/releases/download/$t/$a" \
                || { echo "engine $t: $a failed"; return 1; }
            sha256sum "/root/dl/$a" >> "$RES/hw/engine-sha256.txt"
            tar -C "$d" -xzf "/root/dl/$a" && rm -f "/root/dl/$a"
        done
    fi
    local bin; bin=$(dirname "$(find "$d" -name llama-server -type f | head -1)")
    # same as Enigma gatherLibs: every shared library next to llama-server
    find "$d" -name '*.so*' \( -type f -o -type l \) -not -path "$bin/*" -exec cp -an {} "$bin/" \;
    echo "$bin" > "$d/.bindir"
    LD_LIBRARY_PATH=$bin "$bin/llama-server" --version > "$RES/hw/engine-$t.txt" 2>&1
    LD_LIBRARY_PATH=$bin "$bin/llama-server" --list-devices >> "$RES/hw/engine-$t.txt" 2>&1
    echo "engine $t $(date +%T): $(grep -c CUDA "$RES/hw/engine-$t.txt") CUDA lines"
}
echo "downloads start $(date +%T)" >> "$RES/hw/downloads.txt"
for t in $(J "' '.join(d['engines'].values())"); do eng "$t" & done
dl_model "$(J "d['model']['url']")" "$(J "d['model']['file']")" "$(J "d['model']['sha']")" &
if [ "$(J "bool(d.get('draft'))")" = True ]; then
    dl_model "$(J "d['draft']['url']")" "$(J "d['draft']['file']")" "$(J "d['draft']['sha']")" &
fi
# fork arms with their own model files (card "extra_models": [{url, file, sha}])
for i in $(J "' '.join(str(i) for i in range(len(d.get('extra_models', []))))"); do
    dl_model "$(J "d['extra_models'][$i]['url']")" "$(J "d['extra_models'][$i]['file']")" "$(J "d['extra_models'][$i]['sha']")" &
done
wait
# MTP graft on the host (card "graft": {target, donor (file or URL: only the MTP tensors are fetched), out})
if [ "$(J "bool(d.get('graft'))")" = True ]; then
    gout=/root/models/$(J "d['graft']['out']")
    if [ ! -f "$gout.ok" ]; then
        python3 /root/nv/graft_mtp.py graft "/root/models/$(J "d['graft']['target']")" "$(J "d['graft']['donor']")" "$gout" \
            > "$RES/hw/graft.log" 2>&1 && touch "$gout.ok"
    fi
    echo "graft $(basename "$gout") $(date +%T) ok=$([ -f "$gout.ok" ] && echo yes || echo no)" >> "$RES/hw/downloads.txt"
fi
if [ "$(J "bool(d.get('moe'))")" = True ]; then   # second model after the first: the main arms start sooner
    ( dl_model "$(J "d['moe']['url']")" "$(J "d['moe']['file']")" "$(J "d['moe']['sha']")" ) &
    MOE_PID=$!
fi
echo "downloads done $(date +%T)"; cat "$RES/hw/downloads.txt"
[ -f "/root/models/$(J "d['model']['file']")".ok ] || { echo "model download failed"; exit 1; }
if [ -n "${MOE_PID:-}" ]; then
    # the MoE block runs last; nv67.py waits for its .ok file
    echo "moe download in background (pid $MOE_PID)"
fi
python3 /root/nv/nv67.py "$CARD"
echo "ALL DONE $(date +%T)"
