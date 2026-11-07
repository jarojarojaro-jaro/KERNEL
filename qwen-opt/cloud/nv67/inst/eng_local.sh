#!/usr/bin/env bash
# ON the host, when GitHub downloads crawl: install official engine tarballs that camp.sh `engput` copied to
# /root/dl-local/ (same steps as setup.sh eng()), then stop the slow curl so setup.sh goes on.
#   eng_local.sh <tag> [<tag> ...]
set -uo pipefail
RES=${RES:-/root/res}
for t in "$@"; do
    d=/root/eng/$t
    [ -f "$d/.bindir" ] && { echo "engine $t already installed"; continue; }
    mkdir -p "$d"
    # one cudart tarball serves every tag (same CUDA 12.8 runtime libs in each release)
    cud=/root/dl-local/cudart-llama-$t-bin-ubuntu-cuda-12.8-x64.tar.gz
    [ -f "$cud" ] || cud=$(ls /root/dl-local/cudart-llama-*-bin-ubuntu-cuda-12.8-x64.tar.gz | head -1)
    for a in "/root/dl-local/llama-$t-bin-ubuntu-cuda-12.8-x64.tar.gz" "$cud"; do
        tar -C "$d" -xzf "$a" || { echo "engine $t: bad $a"; exit 1; }
        sha256sum "$a" >> "$RES/hw/engine-sha256.txt"
    done
    bin=$(dirname "$(find "$d" -name llama-server -type f | head -1)")
    find "$d" -name '*.so*' \( -type f -o -type l \) -not -path "$bin/*" -exec cp -an {} "$bin/" \;
    LD_LIBRARY_PATH=$bin "$bin/llama-server" --version > "$RES/hw/engine-$t.txt" 2>&1
    LD_LIBRARY_PATH=$bin "$bin/llama-server" --list-devices >> "$RES/hw/engine-$t.txt" 2>&1
    echo "$bin" > "$d/.bindir"
    pkill -f "curl .*releases/download/$t/" || true
    echo "engine $t installed from /root/dl-local ($(grep -c CUDA "$RES/hw/engine-$t.txt") CUDA lines)"
done
