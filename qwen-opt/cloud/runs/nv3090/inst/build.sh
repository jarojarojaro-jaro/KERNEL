#!/usr/bin/env bash
# ON the instance: build.sh <name>  — builds /root/src/<name> (sm_86 only, ccache) and installs binaries+libs to
# /root/bin/<name>. Flags as the pkg/topka2 build (GGML_NATIVE=OFF + AVX2/FMA/F16C). Log: results/nv3090/build/<name>.log
set -uo pipefail
export CCACHE_BASEDIR=/root CCACHE_NOHASHDIR=true
n=$1; S=/root/src/$n; B=/root/build/$n; O=/root/bin/$n; LOG=/root/results/nv3090/build/$n.log
mkdir -p "$B" "$O"
{
  date
  cmake -S "$S" -B "$B" -G Ninja -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=86 \
      -DGGML_NATIVE=OFF -DGGML_AVX2=ON -DGGML_FMA=ON -DGGML_F16C=ON -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=ON \
      -DCMAKE_C_COMPILER_LAUNCHER=ccache -DCMAKE_CXX_COMPILER_LAUNCHER=ccache -DCMAKE_CUDA_COMPILER_LAUNCHER=ccache \
      -DCMAKE_INSTALL_RPATH='$ORIGIN' -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON
  nice -n 5 cmake --build "$B" -j "${JOBS:-16}" --target llama-server llama-bench test-backend-ops ${EXTRA_TARGETS:-}
  rc=$?
  cp -a "$B"/bin/* "$O"/ 2>/dev/null
  find "$B" -name '*.so*' -exec cp -a {} "$O"/ \;
  echo "rc=$rc $(date)"
} > "$LOG" 2>&1
tail -1 "$LOG"
