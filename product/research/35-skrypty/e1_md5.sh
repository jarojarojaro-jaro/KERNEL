#!/usr/bin/env bash
# Report 35 E1 md5 gate of a static MTP depth (config change rule): fusion/greedy.sh MTP mode, PM4 env as topka.
#   n=4 GV=1 (must be the reference 6f14e814), n=N GV=1 twice (deterministic), n=N GV=0 (GPU verify off == on).
# usage: e1_md5.sh N      outputs /tmp/x35/q-n<d>-gv<g>[-r2].mtp.txt. Run ONLY from the GPU queue.
set -uo pipefail
n=$1
bin=${BIN:-$HOME/llama-topka}/bin
export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0 PORT=${PORT:-18722} MODES=mtp
trap 'pkill -f "$bin/llama-server.*--port $PORT" || true' EXIT
trap 'exit 1' TERM INT
pkill -f 'llama-topka/bin/llama-server' && sleep 5
"$HOME/qwen-opt/lookup/vram_ok.sh" || exit 1
mkdir -p /tmp/x35 && rm -f /tmp/x35/q-*.txt
g() { DRAFT_N=$1 LLAMA_GPU_VERIFY=$2 taskset -c 2-5 "$HOME/qwen-opt/fusion/greedy.sh" "$bin" "$bin" "/tmp/x35/q-n$1-gv$2$3" qwen; }
g 4 1 ""; g "$n" 1 ""; g "$n" 1 "-r2"; g "$n" 0 ""
md5sum /tmp/x35/q-*.mtp.txt | sed 's#/tmp/x35/##' | cut -c1-8,33-
rc=0
[ "$(md5sum < /tmp/x35/q-n4-gv1.mtp.txt | cut -c1-8)" = 6f14e814 ] && echo "n=4 = reference 6f14e814" || { echo "n=4 != 6f14e814"; rc=1; }
cmp -s "/tmp/x35/q-n$n-gv1.mtp.txt" "/tmp/x35/q-n$n-gv1-r2.mtp.txt" && echo "n=$n deterministic" || { echo "n=$n NOT deterministic"; rc=1; }
cmp -s "/tmp/x35/q-n$n-gv1.mtp.txt" "/tmp/x35/q-n$n-gv0.mtp.txt" && echo "n=$n GPU verify off == on" || { echo "n=$n GV off != on"; rc=1; }
cmp -s "/tmp/x35/q-n4-gv1.mtp.txt" "/tmp/x35/q-n$n-gv1.mtp.txt" && echo "n=$n == n=4 (no new reference needed)" || echo "n=$n != n=4: new md5 reference $(md5sum < /tmp/x35/q-n$n-gv1.mtp.txt | cut -c1-8)"
exit $rc
