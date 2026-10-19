#!/usr/bin/env bash
# Runs ON the build server, called by ~/qwen-opt/tools/rbuild over ssh:
#   remote-build.sh <worktree abs path> <build subdir> <commit> <prefix mode 0|1> <jobs> [targets...]
# stdin: cmake -D options (one per line), a line "--manifest--", then `sha1sum` lines of the local destination dir.
# stdout: zstd tar of <build>/bin entries whose content differs from the manifest (plus all symlinks); logs -> stderr.
# The worktree is checked out at the SAME absolute path as on the workstation, so RUNPATHs (<build>/bin) and
# __FILE__ match; prefix mode rewrites the <build>/bin RUNPATH entry to $ORIGIN.
set -euo pipefail
exec 3>&1 1>&2
BF=/root/bf
wt=$1 b=$2 sha=$3 prefix_mode=$4 jobs=$5
shift 5
targets=("$@")

exec 9>> "$BF/active.lock"; flock -s 9                    # idle-kill.sh waits while any build holds this
touch "$BF/last-activity"; trap 'touch "$BF/last-activity"' EXIT

opts=()
while IFS= read -r l; do [ "$l" = --manifest-- ] && break; [ -n "$l" ] && opts+=("$l"); done
manifest=$(mktemp); cat > "$manifest"

mkdir -p "$wt"
# one build per worktree: the checkout is shared by all its build dirs
exec 8>> "$BF/wt-$(printf %s "$wt" | md5sum | cut -c1-12).lock"; flock 8
if [ ! -d "$wt/.git" ]; then
    git init -q "$wt"
    echo "$BF/repo.git/objects" > "$wt/.git/objects/info/alternates"   # objects arrive by git push into repo.git
fi
# a dirty-tree snapshot is checked out, then HEAD is moved back to its parent (the workstation's HEAD, tree kept), so
# build-info/ggml version strings carry the same commit as a local build. state: .git/rbuild-snap = last snapshot
snapf=$wt/.git/rbuild-snap
[ -s "$snapf" ] && git -C "$wt" reset -q --soft "$(cat "$snapf")"   # HEAD/index = worktree again: minimal rewrites
git -C "$wt" checkout -qf --detach "$sha"                 # rewrites only changed files: make stays incremental
rm -f "$snapf"
if [ "$(git -C "$wt" log -1 --format=%an "$sha")" = rbuild ]; then
    git -C "$wt" reset -q --soft HEAD~1; echo "$sha" > "$snapf"
fi

bd=$wt/$b
optsha=$(printf '%s\n' "${opts[@]}" | sha1sum | cut -c1-40)
if [ ! -f "$bd/CMakeCache.txt" ] || [ "$(cat "$bd/.rbuild-opts" 2>/dev/null)" != "$optsha" ]; then
    echo "rbuild[remote]: configuring $bd"
    cmake -S "$wt" -B "$bd" "${opts[@]}" > "$bd.configure.log" 2>&1 || { tail -40 "$bd.configure.log"; exit 1; }
    echo "$optsha" > "$bd/.rbuild-opts"
fi

t0=$(date +%s)
[ "$jobs" = 0 ] && jobs=$(nproc)
tgt=(); [ ${#targets[@]} -gt 0 ] && tgt=(--target "${targets[@]}")
# progress lines dropped (the link is slow); warnings, errors and the summary stay
if ! cmake --build "$bd" -j "$jobs" "${tgt[@]}" -- -l "$(nproc)" 2>&1 | sed -uE '/^\[ *[0-9]+%\] (Building|Linking|Built)/d'; then
    echo "rbuild[remote]: BUILD FAILED"; exit 1
fi
echo "rbuild[remote]: build $(( $(date +%s) - t0 )) s (-j $jobs, $(nproc) cores)"
# the workstation is a Ryzen 7 5700X (Zen 3, no AVX-512): any zmm register in host code means the build server's
# CPU leaked in (ccache-wrap not applied) and the binaries could SIGILL locally
for f in "$bd"/bin/libggml-cpu.so "$bd"/bin/libggml-base.so "$bd"/bin/libllama.so; do
    [ -e "$f" ] || continue
    n=$(objdump -d --no-show-raw-insn "$f" | grep -c zmm || true)
    [ "$n" = 0 ] || { echo "rbuild[remote]: $f has $n zmm (AVX-512) instructions, refusing to ship"; exit 1; }
done

stage=$bd/bin
if [ "$prefix_mode" = 1 ]; then
    stage=$(mktemp -d)
    cp -a "$bd/bin/." "$stage/"
    for f in "$stage"/*; do
        [ -f "$f" ] && [ ! -L "$f" ] || continue
        rp=$(patchelf --print-rpath "$f" 2>/dev/null) || continue
        case $rp in *"$bd/bin"*) patchelf --set-rpath "${rp//$bd\/bin/\$ORIGIN}" "$f" ;; esac
    done
fi
cd "$stage"
send=()
while IFS= read -r -d '' f; do
    if [ -L "$f" ]; then send+=("$f"); continue; fi
    s=$(sha1sum "$f" | cut -c1-40)
    grep -qxF "$s  $f" "$manifest" || send+=("$f")
done < <(find . -maxdepth 1 \( -type f -o -type l \) -printf '%P\0')
if [ ${#send[@]} -eq 0 ]; then
    echo "rbuild[remote]: nothing changed"
    tar -cf - -T /dev/null | zstd -q >&3
else
    echo "rbuild[remote]: sending ${#send[@]} changed entries ($(printf '%s\0' "${send[@]}" | du -csh --files0-from=- | tail -1 | cut -f1) raw)"
    printf '%s\0' "${send[@]}" | tar --null -T - -cf - | zstd -T0 -3 -q >&3
fi
[ "$prefix_mode" = 1 ] && rm -rf "$stage"
rm -f "$manifest"
