#!/bin/bash
for i in $(seq 120); do
  if grep -q "build rc=0" ~/wt/upstream-inkling/build-r15.log 2>/dev/null; then
    exec ~/qwen-opt/queue/run-jobs.sh ~/qwen-opt/inkling/r15.jobs; fi
  grep -q "build rc=[1-9]" ~/wt/upstream-inkling/build-r15.log 2>/dev/null && { echo "build failed"; exit 1; }
  sleep 30
done
