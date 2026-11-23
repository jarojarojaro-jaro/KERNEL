#!/bin/bash
for i in $(seq 120); do
  if grep -q "build rc=0" ~/wt/upstream-inkling/build-r12.log 2>/dev/null; then
    touch ~/k134/STOP-MAYA; for j in $(seq 60); do ps -eo args | grep -q "^/bin/bash /home/jaro/k134/[m]ayaserve.sh" || break; sleep 5; done
    exec ~/qwen-opt/queue/run-jobs.sh ~/qwen-opt/inkling/r12.jobs; fi
  grep -q "build rc=[1-9]" ~/wt/upstream-inkling/build-r12.log 2>/dev/null && { echo "build failed"; exit 1; }
  sleep 30
done
