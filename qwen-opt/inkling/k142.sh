#!/bin/bash
# K-142: DPP warp xor (branch ad-dpp = production ad-q4k + lane_xor) vs production maya-ik2.adq4k; AtomicChat, lookup, KV q4
set -u; cd ~/k134
P=$HOME/k134/maya/build-hip/maya-ik2.adq4k; D=$HOME/k134/wt-ad-dpp/build-hip/maya-ik2
case $1 in
  test) LD_LIBRARY_PATH=/opt/rocm/core-10.0/lib IK2_HIP_EXPV=1 IK2_HIP_NT=15 IK2_HIP_LGD=2 IK2_HIP_MVF16=1 timeout 280 ~/k134/wt-ad-dpp/build-hip/ik2_kernels_test > /tmp/k142-test.log 2>&1; echo rc=$?; grep -cE "^ok" /tmp/k142-test.log; grep -E "FAIL|passed" /tmp/k142-test.log | head ;;
  run) shift; sed "s#$P#$D#; s#maya-atomic.log#k142-dpp.log#" ~/k134/maya-atomic.json > ~/k134/k142-dpp.json
       for a in "$@"; do c=~/k134/maya-atomic.json; [ $a = dpp ] && c=~/k134/k142-dpp.json; ~/k134/hipx/rep2.sh k142-$a-$RANDOM $c | grep "decode median"; done ;;
  parity) sed "s#$P#$D#; s#maya-atomic.log#k142-dpp.log#" ~/k134/maya-atomic.json > ~/k134/k142-dpp.json
    for a in prod dpp; do c=~/k134/maya-atomic.json; [ $a = dpp ] && c=~/k134/k142-dpp.json; LD_LIBRARY_PATH=/opt/rocm/core-10.0/lib ./ablate/gen.sh k142-par-$a $c > /dev/null 2>&1; done
    python3 -c "
import json; a=json.load(open('/home/jaro/k134/ablate/k142-par-prod.json')); b=json.load(open('/home/jaro/k134/ablate/k142-par-dpp.json'))
d=[k for k in a if a[k]['answer']!=b.get(k,{}).get('answer')]; print('parity prod vs dpp:', 'IDENTICAL' if not d else 'DIFF '+','.join(d), len(a))" ;;
esac
