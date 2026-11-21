#!/bin/bash
# run from the Jarvo server when jaroserverai is back: push inkling-opt, rebuild, queue the r8 gate
set -e
cd ~/praca/llama-inkling && git push -q -f jaro@jaroserverai:llama.cpp inkling-opt:inkling-opt-in
scp -q ~/KERNEL/qwen-opt/inkling/{r8.sh,r9.sh,r8.jobs,when-r8.sh} jaro@jaroserverai:qwen-opt/inkling/
ssh -n jaro@jaroserverai 'cd ~/wt/upstream-inkling && git checkout -q -B inkling-opt inkling-opt-in && sed "s|build-r3.log|build-r8.log|g" build-r3.sh > build-r8.sh && chmod +x build-r8.sh && (setsid nohup ./build-r8.sh > /dev/null 2>&1 < /dev/null &); cd ~/qwen-opt/inkling && (setsid nohup ./when-r8.sh > when-r8.log 2>&1 < /dev/null &); sleep 1; ps -eo pid,args | grep -E "[w]hen-r8|[b]uild-r8" | cut -c1-40'
