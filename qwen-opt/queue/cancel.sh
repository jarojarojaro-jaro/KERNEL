#!/bin/bash
# Cancel one queued/running jobs file safely: stops the run-jobs.sh process AND its whole descendant tree (the running
# job closes the lock fds, so killing only run-jobs.sh would release the GPU lock while the job keeps using the GPU;
# 2026-10-21 a leftover test-backend-ops overlapped the next job for ~10 s).
# GPU processes get SIGTERM and up to 45 s to exit cleanly; SIGKILL only if they are still alive after that.
# 2026-10-21 04:07: a SIGKILL 3 s after SIGTERM hit a llama-server in the middle of a PM4 tape -> SQC (inst) page
# fault on teardown (no reset). Never SIGKILL a GPU process early.
#   cancel.sh <jobs-file-substring>
set -u
pat=${1:?jobs file name or substring}
desc() { local c; for c in $(pgrep -P "$1"); do desc "$c"; echo "$c"; done; }
alive() { local p; for p in "$@"; do kill -0 "$p" 2>/dev/null && return 0; done; return 1; }
for p in $(pgrep -f "run-jobs.sh .*${pat}"); do
    kids=$(desc "$p")
    echo "cancel: run-jobs $p + $(echo $kids | wc -w) descendants"
    # children first (servers exit and free the GPU), the runner last so it cannot start the next job meanwhile
    kill -STOP "$p" 2>/dev/null
    kill -TERM $kids 2>/dev/null
    for _ in $(seq 45); do alive $kids || break; sleep 1; done
    alive $kids && { echo "cancel: still alive after 45 s, SIGKILL"; kill -KILL $kids 2>/dev/null; }
    kill -TERM "$p" 2>/dev/null; kill -CONT "$p" 2>/dev/null
done
pgrep -af "run-jobs.sh .*${pat}" | grep -v pgrep || echo "cancel: done"
