#!/usr/bin/env bash
# Stage topka-q70 (topka-q63 c0576e3e8 + cachesave #30137/HUGE + fa-d256 VAR 83) as ~/llama-topka.q70:
# copy of build-hip/bin with the build-dir RUNPATH entry rewritten to $ORIGIN (same layout as ~/llama-topka). CPU only.
set -euo pipefail
B=$HOME/wt/l1-cachesave/build-hip; T=$HOME/llama-topka.q70
rm -rf "$T"; mkdir -p "$T"; cp -a "$B/bin" "$T/bin"
for f in "$T"/bin/*; do
    [ -L "$f" ] && continue
    rp=$(patchelf --print-rpath "$f" 2>/dev/null) || continue
    case $rp in *"$B/bin"*) patchelf --set-rpath "${rp//$B\/bin/\$ORIGIN}" "$f" ;; esac
done
git -C "$HOME/wt/l1-cachesave" log --oneline -1 | cut -c1-80 > "$T/ENGINE"
! grep -l "$B" "$T"/bin/* 2>/dev/null | xargs -r readelf -d 2>/dev/null | grep -q "$B" || { echo "build path left in RUNPATH"; exit 1; }
# ROCm libs resolve through the system loader path exactly as for ~/llama-topka: compare, don't demand zero.
[ "$(ldd "$T/bin/libggml-hip.so" | grep -c 'not found')" = "$(ldd "$HOME/llama-topka/bin/libggml-hip.so" | grep -c 'not found')" ] \
    || { echo "lib resolution differs from production"; exit 1; }
echo "staged $T: $(ls "$T/bin" | wc -l) files, $(cat "$T/ENGINE")"
