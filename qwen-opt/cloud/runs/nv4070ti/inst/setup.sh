#!/usr/bin/env bash
# ON the 4070 Ti box (nvidia/cuda:12.8.1-devel-ubuntu24.04): deps, model downloads (background), hw snapshot,
# source unpack, nsys. Builds are separate (bld.sh) so benchmarks never overlap a compile.
set -uo pipefail
H=/root/cloud; S=/root/src; M=/root/models; RES=/root/results/opt-4070ti-20261020
mkdir -p "$S" "$M" "$RES/hw" "$RES/build" "$RES/logs" "$RES/gate"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq && apt-get install -y -qq --no-install-recommends git cmake ninja-build ccache build-essential \
    libssl-dev curl ca-certificates jq python3 aria2 bc rsync zstd procps libgomp1 util-linux > "$RES/build/apt.log" 2>&1
echo "apt rc=$?"
dl() {  # url file sha
    aria2c -q -x 8 -s 8 -c --file-allocation=none --checksum="sha-256=$3" -d $M -o "$2" "$1" && touch "$M/$2.ok"
    echo "$2 $(date +%T) ok=$([ -f $M/$2.ok ] && echo yes || echo no)" >> "$RES/build/downloads.txt"
}
echo "downloads start $(date +%T)" >> "$RES/build/downloads.txt"
U=https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/resolve/4ca720788d1e01f1bff70c033e0d0028fd02e502
( dl $U/Qwen3.8-27B-UD-IQ3_XXS.gguf Qwen3.8-27B-UD-IQ3_XXS.gguf c0b7c3038681ed2e3040456c1dd45f9858b6c2290bed172c70388a94874f3eee
  dl $U/Qwen3.8-27B-UD-Q2_K_XL.gguf Qwen3.8-27B-UD-Q2_K_XL.gguf fd4730dd8aad070517978752b63d530aeb1740d2283cab9fa24f1e404032ddb0 ) &
for t in upstream nv; do mkdir -p $S/$t && tar -C $S/$t --zstd -xf $H/$t.tar.zst; done
nvidia-smi -q > "$RES/hw/nvidia-smi-q.txt"
{ uname -a; lscpu; free -g; df -h /root; nproc; cat /sys/fs/cgroup/cpu.max; nvcc --version; cat /root/qwenbench-label; } > "$RES/hw/system.txt" 2>&1
apt-get install -y -qq --no-install-recommends nsight-systems-2025.1.1 > "$RES/build/nsys-apt.log" 2>&1 \
  || apt-get install -y -qq --no-install-recommends cuda-nsight-systems-12-8 >> "$RES/build/nsys-apt.log" 2>&1
echo "nsys: $(command -v nsys || ls /opt/nvidia/nsight-systems/*/bin/nsys 2>/dev/null)"
wait
echo "setup done $(date +%T)"
