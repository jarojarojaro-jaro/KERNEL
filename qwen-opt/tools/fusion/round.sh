#!/usr/bin/env bash
# usage: round.sh MODEL TAG LABEL...   (LABEL = bins dir name or "base")
cd "$(dirname "$0")"
model=$1; tag=$2; shift 2
for b in "$@"; do
    if [ "$b" = base ]; then bin=$HOME/llama-opt/bin; lib=$HOME/llama-opt/lib; else bin=$PWD/bins/$b; lib=$PWD/bins/$b; fi
    flock -o /tmp/gpu.lock ./bench.sh "$tag-$b-$model" "$bin" "$lib" "$model" 2>&1 | grep -v "^$"
    sleep 30
done
