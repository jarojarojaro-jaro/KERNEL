#!/bin/bash
# start the Inkling baseline once the build and the two model files are complete (checks every 2 min, gives up after 4 h)
for i in $(seq 120); do
  if grep -q "build rc=0" ~/wt/upstream-inkling/build.log 2>/dev/null && grep -q "done Inkling-2-Mini-Uncensored-AD-Q4_K.gguf" ~/models/inkling/dl.log \
     && grep -q "done dspark-Inkling-2-Mini-Q8_0.gguf" ~/models/inkling/dl.log; then
    echo "$(date +%T) ready, queueing base.jobs"; exec ~/qwen-opt/queue/run-jobs.sh ~/qwen-opt/inkling/base.jobs
  fi
  grep -q "build rc=[1-9]" ~/wt/upstream-inkling/build.log 2>/dev/null && { echo "$(date +%T) build failed"; exit 1; }
  sleep 120
done
