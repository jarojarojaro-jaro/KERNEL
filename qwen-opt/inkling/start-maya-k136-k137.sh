#!/bin/bash
# K-136 (Maya v1.1.75 + hipx14 port, DSpark GGUF drafter) and K-137 (AtomicChat AD-Q4_K natively: Q4_K/Q5_0 experts).
# Run on the Jarvo server when jaroserverai is on and the owner said "tak": pushes both branches, builds on the box
# (cpuheavy, no GPU lock), then queues the gate. Production build ~/k134/maya/build-hip/maya-ik2.hipx14 is untouched.
set -e
cd ~/kernel/zrodla/maya
for b in k175 ad-q4k k175-ad; do git push -q -f jaro@jaroserverai:k134/maya-git.git "$b:$b" 2>/dev/null || {
  ssh -n jaro@jaroserverai 'git init -q --bare ~/k134/maya-git.git'; git push -q -f jaro@jaroserverai:k134/maya-git.git "$b:$b"; }; done
scp -q ~/KERNEL/qwen-opt/inkling/maya-k13x.sh ~/KERNEL/qwen-opt/inkling/maya-k13x.jobs jaro@jaroserverai:k134/
ssh -n jaro@jaroserverai 'cd ~/k134 && for b in k175 ad-q4k k175-ad; do [ -d wt-$b ] || git clone -q maya-git.git wt-$b; (cd wt-$b && git fetch -q origin && git checkout -q -B $b origin/$b); done
  OPTS=$(grep -E "^(MAYA_|STRATA_|CMAKE_BUILD_TYPE|CMAKE_HIP_ARCHITECTURES|GPU_TARGETS|AMDGPU_TARGETS)[A-Z_]*:" maya/build-hip/CMakeCache.txt | sed "s/^\([^:]*\):[^=]*=\(.*\)/-D\1=\2/" | tr "\n" " ")
  cat > build-k13x.sh <<EOF
#!/bin/bash
for b in k175 ad-q4k k175-ad; do cd ~/k134/wt-\$b && cmake -S . -B build-hip $OPTS -DSTRATA_BUILD_TESTS=ON -DMAYA_BUILD_TESTS=ON > ../build-\$b.log 2>&1 && cpuheavy --quiet cmake --build build-hip -j2 --target maya-ik2 ik2_kernels_test >> ../build-\$b.log 2>&1; echo "build \$b rc=\$?" >> ../build-k13x.done; done
EOF
  chmod +x build-k13x.sh; rm -f build-k13x.done; (setsid nohup ./build-k13x.sh > /dev/null 2>&1 < /dev/null &)
  (setsid nohup bash -c "while [ \$(grep -c rc= build-k13x.done 2>/dev/null || echo 0) -lt 3 ]; do sleep 30; done; grep -q \"rc=[1-9]\" build-k13x.done || ~/qwen-opt/queue/run-jobs.sh ~/k134/maya-k13x.jobs" > when-k13x.log 2>&1 < /dev/null &)
  echo started'
