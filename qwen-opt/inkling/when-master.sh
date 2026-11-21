#!/bin/bash
# queue the Inkling baseline (unsloth UD-Q4_K_XL, master build) once ~/wt/upstream-master is built
for i in $(seq 90); do
  grep -q "build rc=0" ~/wt/upstream-master/build.log 2>/dev/null && exec ~/qwen-opt/queue/run-jobs.sh ~/qwen-opt/inkling/base.jobs
  grep -q "build rc=[1-9]" ~/wt/upstream-master/build.log 2>/dev/null && { echo "master build failed"; exit 1; }
  sleep 60
done
