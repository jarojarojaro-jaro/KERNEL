#!/usr/bin/env bash
# Report 35 chain: GPU queue x35-b (E1 follow-up), then the E5 build of ~/wt/bxadapt (topka + adapt-spec + batch-invariant)
# locally (rbuild --local: cpuheavy --quiet holds /tmp/quiet.lock shared, so no GPU job runs during the build), then
# the GPU queue x35-c (E5 gates and A/B) if its jobs file exists.
set -u
q=$HOME/qwen-opt/queue
"$q/run-jobs.sh" "$q/x35-b.jobs"
mapfile -t opts < "$HOME/qwen-opt/xtxlab/bx-cmake-opts.txt"
[ -f "$HOME/wt/bxadapt/build-hip/CMakeCache.txt" ] || \
    "$HOME/qwen-opt/tools/cpuheavy" cmake -S "$HOME/wt/bxadapt" -B "$HOME/wt/bxadapt/build-hip" "${opts[@]}"
t0=$(date +%s)
"$HOME/qwen-opt/tools/rbuild" --local "$HOME/wt/bxadapt" llama-server test-backend-ops
rc=$?; echo "build rc=$rc $(( $(date +%s) - t0 )) s"; [ $rc = 0 ] || exit $rc
[ -f "$q/x35-c.jobs" ] && "$q/run-jobs.sh" "$q/x35-c.jobs"
