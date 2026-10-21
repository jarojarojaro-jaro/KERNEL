#!/bin/bash
# Cancel one queued/running jobs file safely: kills the run-jobs.sh process AND its whole descendant tree (the running
# job closes the lock fds, so killing only run-jobs.sh would release the GPU lock while the job keeps using the GPU;
# 2026-10-21 a leftover test-backend-ops overlapped the next job for ~10 s).
#   cancel.sh <jobs-file-substring>
set -u
pat=${1:?jobs file name or substring}
desc() { local c; for c in $(pgrep -P "$1"); do desc "$c"; echo "$c"; done; }
for p in $(pgrep -f "run-jobs.sh .*${pat}"); do
    kids=$(desc "$p")
    echo "cancel: run-jobs $p + $(echo $kids | wc -w) descendants"
    kill -TERM $p $kids 2>/dev/null
    sleep 3
    kill -KILL $p $kids 2>/dev/null
done
pgrep -af "run-jobs.sh .*${pat}" | grep -v pgrep || echo "cancel: done"
