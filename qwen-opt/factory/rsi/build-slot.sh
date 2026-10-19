#!/usr/bin/env bash
# RSI-F build slot: every workspace is built in ONE fixed build tree (~/wt/rsi-slot), so after the first full build
# only the files a workspace changed are recompiled (user CPU rule: 2 cores, one heavy job at a time).
#   cpuheavy --quiet bash rsi/build-slot.sh WORKSPACE -j2
# Copies WORKSPACE (incl. its one-commit .git, so build-info carries the workspace commit) into the slot with
# checksums and fresh mtimes (a file that changed back still triggers a rebuild), builds, installs into WORKSPACE/inst.
# Only one caller at a time: the caller holds a cpuheavy slot; the slot itself is guarded by /tmp/rsi-slot.lock.
set -euo pipefail
WS=$(readlink -f "${1:?workspace}")
JOBS=${2:--j2}
[ "$JOBS" = "-j1" ] || [ "$JOBS" = "-j2" ] || { echo "jobs must be -j1 or -j2" >&2; exit 2; }
SLOT=${RSI_SLOT:-$HOME/wt/rsi-slot}
mkdir -p "$SLOT/src"
exec 9>/tmp/rsi-slot.lock
flock 9
rsync -r -l --checksum --no-times --delete --exclude /build --exclude /inst "$WS/" "$SLOT/src/"
if [ ! -f "$SLOT/build/CMakeCache.txt" ]; then
  cmake -S "$SLOT/src" -B "$SLOT/build" -DGGML_HIP=ON -DGPU_TARGETS=gfx1100 -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_PREFIX_PATH=/opt/rocm/core-10.0 -DCMAKE_HIP_COMPILER=/opt/rocm/core-10.0/lib/llvm/bin/clang++ \
    -DGGML_HIP_NO_VMM=ON -DGGML_HIP_GRAPHS=ON -DGGML_HIP_MMQ_MFMA=ON -DGGML_NATIVE=ON -DLLAMA_CURL=OFF \
    -DGGML_CCACHE=OFF -DCMAKE_INSTALL_PREFIX="$SLOT/inst"
fi
cmake --build "$SLOT/build" "$JOBS"
rm -rf "$WS/inst"
cmake --install "$SLOT/build" --prefix "$WS/inst" > /dev/null
echo "built $(git -C "$WS" rev-parse --short HEAD) -> $WS/inst"
