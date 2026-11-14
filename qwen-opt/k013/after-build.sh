#!/usr/bin/env bash
# waits for the fewrow-hip build, then queues the V(w) bench (detached). Log ~/qwen-opt/k013/after-build.log
for i in $(seq 360); do grep -q "^rc=" ~/wt/fewrow-hip/build.log 2>/dev/null && break; sleep 20; done
tail -1 ~/wt/fewrow-hip/build.log
grep -q "^rc=0" ~/wt/fewrow-hip/build.log || { echo "build failed"; exit 1; }
cd ~/qwen-opt && ./queue/run-jobs.sh ~/qwen-opt/k013/k013-fewrow.jobs
