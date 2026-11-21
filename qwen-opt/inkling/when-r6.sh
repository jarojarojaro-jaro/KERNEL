#!/bin/bash
# run the ink-r2 gate after the opt build and the AtomicChat download (and after the stock baseline queue started)
for i in $(seq 240); do
  if grep -q "build rc=0" ~/wt/upstream-inkling/build-r6.log 2>/dev/null ; then
    exec ~/qwen-opt/queue/run-jobs.sh ~/qwen-opt/inkling/r6.jobs; fi
  grep -q "build rc=[1-9]" ~/wt/upstream-inkling/build-r6.log 2>/dev/null && { echo "opt build failed"; exit 1; }
  sleep 60
done
