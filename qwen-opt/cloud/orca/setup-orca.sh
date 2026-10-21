#!/usr/bin/env bash
# Build stage for the OrcaCyber-3090 campaign. Runs ON the instance (nvidia/cuda:12.8.1-devel-ubuntu24.04).
# Starts the gated HF download in the background, then builds upstream base + our fork (topka) with CUDA sm_86.
# models.tsv in this directory is header-only on purpose: bootstrap.sh must not pull the other model set.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
export DEBIAN_FRONTEND=noninteractive
mkdir -p /root/models /root/results

apt-get update -qq
apt-get install -y -qq --no-install-recommends git cmake ninja-build ccache build-essential libssl-dev \
    curl ca-certificates jq python3 aria2 rsync pciutils procps

setsid nohup bash "$HERE/download-orca.sh" > /root/download-orca.log 2>&1 < /dev/null &
dl=$!
echo "$(date -u +%T) download pid $dl -> /root/download-orca.log"

cd "$HERE"
./bootstrap.sh --go
wait "$dl" || { echo "MODEL DOWNLOAD FAILED, see /root/download-orca.log" >&2; exit 1; }
ls -l /root/models
echo "$(date -u +%T) setup done"
