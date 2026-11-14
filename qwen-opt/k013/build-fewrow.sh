#!/usr/bin/env bash
# K-013: upstream llama.cpp 6ad15f48 (#31533 few-row MMQ + HIP RDNA3 WMMA port), gfx1100 only, llama-bench only.
cd ~/wt/fewrow-hip
HIPCXX="$(hipconfig -l)/clang" HIP_PATH="$(hipconfig -R)" cmake -S . -B build-hip -DGGML_HIP=ON -DGPU_TARGETS=gfx1100 \
  -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_SERVER=OFF > build-cmake.log 2>&1
cmake --build build-hip --target llama-bench -j4 > build.log 2>&1
echo "rc=$? $(date -u +%T)" >> build.log
