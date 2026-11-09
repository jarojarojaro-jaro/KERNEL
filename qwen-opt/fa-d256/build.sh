#!/usr/bin/env bash
# Step 1 of fa-d256.jobs (inside the GPU job, Main's OK 2026-11-07): minimal build of ~/wt/fa-d256.
set -uo pipefail
. "$HOME/qwen-opt/fa-d256/common.sh"
rm -f "$D/BUILD_OK"
cd "$HOME/wt/fa-d256" || exit 1
t0=$(date +%s)
nice -n 19 taskset -c 0-3 cmake --build build-hip -j4 --target test-backend-ops llama-server llama-bench > "$D/logs/build.log" 2>&1
rc=$?
echo "build rc=$rc $(( $(date +%s) - t0 )) s"
[ $rc = 0 ] || { grep -m20 -E "error|Error" "$D/logs/build.log"; tail -20 "$D/logs/build.log"; exit 1; }
git log --oneline -1 | cut -c1-120; git diff --stat | tail -1
touch "$D/BUILD_OK"
