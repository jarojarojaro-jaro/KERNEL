#!/usr/bin/env bash
# ON the 4060 Ti box: build.sh <srcdir> <outname> [extra targets...] — sm_89 Release build (ccache), binaries + libs
# copied to /root/bin/<outname> with HEAD.txt. Never run while a benchmark runs (lekcja-obciazenie-cpu).
set -euo pipefail
src=$1; out=$2; shift 2
targets=(llama-server llama-bench test-backend-ops "$@")
cd "$src"
[ -f b89/CMakeCache.txt ] || cmake -S . -B b89 -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=89 \
    -DLLAMA_CURL=OFF -DLLAMA_OPENSSL=OFF > b89.cfg.log 2>&1
t0=$(date +%s)
cmake --build b89 -j 6 --target "${targets[@]}" > b89.build.$out.log 2>&1
mkdir -p /root/bin/$out
cp -a b89/bin/* /root/bin/$out/
cat /root/src/HEAD-$(basename "$src").txt > /root/bin/$out/HEAD.txt 2>/dev/null || true
echo "build $out OK in $(( $(date +%s) - t0 )) s"
