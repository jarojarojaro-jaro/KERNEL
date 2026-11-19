#!/bin/bash
# wait for the K-001 instrumented build (rbuild --prefix ~/qwen-opt/k001/inst), then queue its job (run-jobs takes the GPU lock)
sleep 5
while pgrep -f "rbuild --local --prefix $HOME/qwen-opt/k001/inst" > /dev/null; do sleep 15; done
grep -q "copied to" ~/qwen-opt/k001/build.log && exec ~/qwen-opt/queue/run-jobs.sh ~/qwen-opt/k001/k001log.jobs
echo "build failed" >&2
exit 1
