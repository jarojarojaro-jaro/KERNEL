#!/bin/bash
# run from the Jarvo server when jaroserverai is on (after the owner's OK): push inkling-opt, build, queue the r15 gate
set -e
cd ~/praca/llama-inkling && git push -q -f jaro@jaroserverai:llama.cpp inkling-opt:inkling-opt-in
scp -q ~/KERNEL/qwen-opt/inkling/{r15.sh,r15.jobs,when-r15.sh} jaro@jaroserverai:qwen-opt/inkling/
ssh -n jaro@jaroserverai 'cd ~/wt/upstream-inkling && git checkout -q -B inkling-opt inkling-opt-in && sed "s|build-r3.log|build-r15.log|g" build-r3.sh > build-r15.sh && chmod +x build-r15.sh && (setsid nohup ./build-r15.sh > /dev/null 2>&1 < /dev/null &); cd ~/qwen-opt/inkling && (setsid nohup ./when-r15.sh > when-r15.log 2>&1 < /dev/null &); echo started'
