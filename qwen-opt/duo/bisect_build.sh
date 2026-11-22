#!/bin/bash
# K-001 prefill bisect builds (CPU only, outside the GPU lock): one detached worktree ~/wt/duo-bisect, configured like
# ~/wt/l1-cachesave/build-hip, checked out commit by commit (chronological, incremental), llama-bench bin dir copied to
# ~/wt/duo-bisect-<sha>/bin. Usage: bisect_build.sh [sha...]
set -eu
SHAS=${*:-9937409 556ad79 a557fc3 5ff6a15 0bb43ee}
W=~/wt/duo-bisect
[ -d $W ] || git -C ~/wt/l1-cachesave worktree add -q --detach $W ${SHAS%% *}
cd $W
[ -f build/CMakeCache.txt ] || cmake -S . -B build -DGGML_HIP=ON -DGPU_TARGETS=gfx1100 -DCMAKE_BUILD_TYPE=Release \
    -DGGML_HIP_GRAPHS=ON -DGGML_HIP_NO_VMM=ON -DGGML_HIP_MMQ_MFMA=ON -DCMAKE_HIP_COMPILER=/opt/rocm/llvm/bin/clang \
    -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_MTMD=OFF -DLLAMA_BUILD_UI=OFF
for s in $SHAS; do
    [ -x ~/wt/duo-bisect-$s/bin/llama-bench ] && { echo "== $s already built"; continue; }
    git checkout -q --detach $s
    echo "== $s $(date -u +%T) building"
    nice -n 10 cmake --build build -j2 --target llama-bench
    rm -rf ~/wt/duo-bisect-$s && mkdir -p ~/wt/duo-bisect-$s && cp -a build/bin ~/wt/duo-bisect-$s/
    echo "== $s $(date -u +%T) copied to ~/wt/duo-bisect-$s/bin"
done
echo "== all built"
