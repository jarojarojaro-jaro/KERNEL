#!/usr/bin/env bash
# Runs ON the build server (ubuntu:24.04, root), started by buildfarm.sh up. Installs the exact local toolchains:
#   - ROCm 10.0.0~pre4-32424980240 (same debs as the workstation, repo.radeon.com/rocmradeon/apt/26.14) -> /opt/rocm/core-10.0
#   - CUDA 12.8 conda env from the workstation's explicit package list -> /home/jaro/opt/cuda-12.8 (same path)
#   - Ubuntu gcc 13.3 / cmake 3.28 / ccache from noble-updates; /usr/local/bin/ccache wraps ccache and turns
#     -march=native into the workstation's expansion (native-flags), so CPU code is built for the Ryzen 5700X
# Files expected next to it in /root/bf: rocm.gpg cuda-explicit.txt native-flags ccache-wrap idle-kill.sh remote-build.sh
set -euo pipefail
BF=/root/bf
ROCM_VER=10.0.0~pre4-32424980240
CUDA_PREFIX=/home/jaro/opt/cuda-12.8
cd "$BF"
touch "$BF/last-activity"
export DEBIAN_FRONTEND=noninteractive

# the idle killer first: a setup that hangs must not keep the box alive
chmod +x "$BF"/*.sh "$BF/ccache-wrap"
pgrep -f "$BF/idle-kill.sh" > /dev/null || setsid nohup "$BF/idle-kill.sh" > "$BF/idle-kill.log" 2>&1 < /dev/null &

apt-get update -qq
apt-get install -y -qq --no-install-recommends ca-certificates curl git zstd bzip2 ccache cmake make build-essential \
    gcc-13 g++-13 patchelf pkg-config python3 python3-venv jq file procps > /dev/null

install -D -m 644 "$BF/rocm.gpg" /etc/apt/keyrings/rocm.gpg
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/rocm.gpg] https://repo.radeon.com/rocmradeon/apt/26.14 noble main" \
    > /etc/apt/sources.list.d/rocm.list

# CUDA (conda) in the background while apt installs ROCm
(
    curl -fsSL https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xj -C /usr/local bin/micromamba
    mkdir -p "$(dirname "$CUDA_PREFIX")"
    MAMBA_ROOT_PREFIX=/root/mamba /usr/local/bin/micromamba create -y -q -p "$CUDA_PREFIX" --file "$BF/cuda-explicit.txt"
) > "$BF/cuda.log" 2>&1 &
cuda_pid=$!

apt-get update -qq
apt-get install -y -qq "amdrocm-core-dev10.0-gfx1100=$ROCM_VER" > "$BF/rocm-apt.log" 2>&1 \
    || { tail -30 "$BF/rocm-apt.log"; exit 1; }
wait "$cuda_pid" || { tail -30 "$BF/cuda.log"; exit 1; }

install -m 755 "$BF/ccache-wrap" /usr/local/bin/ccache
ccache --max-size=25G > /dev/null
git config --global gc.auto 0
git config --global advice.detachedHead false
[ -d "$BF/repo.git" ] || git clone -q --bare https://github.com/ggml-org/llama.cpp "$BF/repo.git"
git -C "$BF/repo.git" config receive.denyCurrentBranch ignore

touch "$BF/last-activity"
echo "SETUP OK"
