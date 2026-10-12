#!/usr/bin/env bash
# Build mtp_extract against the installed fork (~/llama-opt) using the fork's headers (~/llama-master).
set -euo pipefail
cd "$(dirname "$0")"
src=${LLAMA_SRC:-$HOME/llama-master}
lib=${LLAMA_LIB:-$HOME/llama-opt/lib}
nice g++ -O2 -std=c++17 -I"$src/include" -I"$src/ggml/include" -I"$src/src" mtp_extract.cpp -o mtp_extract \
    -L"$lib" -lllama -lggml -lggml-base -Wl,-rpath,"$lib" -Wl,-rpath-link,/opt/rocm/core-10.0/lib
