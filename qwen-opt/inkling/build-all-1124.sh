#!/bin/bash
# owner 2026-11-24 02:31: GPU tests run while builds go. Builds take cpuheavy slot 0 (cores 0-1, nice 19) without
# /tmp/quiet.lock; GPU test servers are pinned to cores 2-5. Done markers in ~/k134/build-all.done.
D=~/k134/build-all.done; : > $D
B() { flock /tmp/cpuheavy.0.lock nice -n 19 taskset -c 0-1 "$@"; }
cd ~/wt/upstream-inkling && B cmake --build build-hip -j2 --target llama-server llama-bench test-backend-ops llama-perplexity > build-r15.log 2>&1; echo "r15 rc=$?" >> $D
for b in ad-q4k k175-ad k175; do cd ~/k134/wt-$b && B bash -c "cmake -S . -B build-hip $(cat ~/k134/maya-cmake-opts) -DSTRATA_BUILD_TESTS=ON -DMAYA_BUILD_TESTS=ON && cmake --build build-hip -j2 --target maya-ik2 ik2_kernels_test" > ../build-$b.log 2>&1; echo "$b rc=$?" >> $D; done
