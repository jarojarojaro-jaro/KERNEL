#!/usr/bin/env bash
# aob-v1 HIP build recipe (run by the implementer inside its workspace; CPU only, no GPU).
# Snapshot step (done by the planner before the agent phase): the workspace $WS/src is a ONE-COMMIT snapshot of
# base_commit WITHOUT history, e.g.  git -C ~/llama-master archive BASE | tar -x -C $WS/src  && git -C $WS/src init &&
# git -C $WS/src add -A && git -C $WS/src commit -qm base   (no oracle commits, no patch series, no reflog).
set -euo pipefail
WS=${WS:?set WS to the task workspace}
cd "$WS/src"
flock -s /tmp/quiet.lock flock /tmp/cpuheavy.lock nice -n 19 taskset -c 0-1 cmake -S . -B "$WS/build" \
  -DGGML_HIP=ON -DGPU_TARGETS=gfx1100 -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH=/opt/rocm/core-10.0 -DCMAKE_HIP_COMPILER=/opt/rocm/core-10.0/lib/llvm/bin/clang++ \
  -DGGML_HIP_NO_VMM=ON -DGGML_HIP_GRAPHS=ON -DGGML_HIP_MMQ_MFMA=ON -DLLAMA_CURL=OFF \
  -DCMAKE_INSTALL_PREFIX="$WS/inst"
flock -s /tmp/quiet.lock flock /tmp/cpuheavy.lock nice -n 19 taskset -c 0-1 cmake --build "$WS/build" -j2
flock -s /tmp/quiet.lock flock /tmp/cpuheavy.lock nice -n 19 taskset -c 0-1 cmake --install "$WS/build"
