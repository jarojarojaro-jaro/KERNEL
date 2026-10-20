#!/usr/bin/env bash
R=https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/resolve/4ca720788d1e01f1bff70c033e0d0028fd02e502
while ! command -v aria2c >/dev/null; do sleep 5; done
mkdir -p /root/models
dl() { aria2c -q -x 16 -s 16 -c --file-allocation=none --checksum=sha-256=$2 -d /root/models -o $1 $R/$1 && touch /root/models/$1.ok; echo "$1 $(date +%T) ok=$([ -f /root/models/$1.ok ] && echo y || echo n)" >> /root/results/nv3090/build/downloads.txt; }
dl Qwen3.8-27B-UD-Q6_K_M.gguf 493301830a596b8ad56dc1329f80bbcb578c8e910da395feafdc9cd8263430bb &
wait
