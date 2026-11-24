#!/bin/bash
# K-143: Inkling decode at long context (IK2_DEPTH puts the prompt at position N; earlier cache = zeros, same bytes read)
# Maya 1.1.75 + hipx14 + Q4_K/Q5_0 (wt-k175-ad), AtomicChat AD-Q4_K, plain decode (no drafting), KV q4 vs f16
set -u; cd ~/k134/hipx
X=$HOME/k134/wt-k175-ad/build-hip/maya-ik2; AD=$HOME/models/inkling/Inkling-2-Mini-Uncensored-AD-Q4_K.gguf
export LD_LIBRARY_PATH=/opt/rocm/core-10.0/lib IK2_HIP_COMB=1 IK2_HIP_EXPV=1 IK2_HIP_FUSE=1 IK2_HIP_LGD=2 IK2_HIP_LGR=1 IK2_HIP_MVF16=1 IK2_HIP_NT=15 IK2_HIP_PCONV=1
for kv in q4 f16; do for d in 0 8192 32768 131072; do
  if [ $kv = q4 ]; then e="IK2_KV=q4"; else e="IK2_KV_DUMMY=1"; fi
  r=$(env $e IK2_DEPTH=$d timeout 240 taskset -c 2-5 $X --model $AD --tokens @short.tok --gen 128 --ctx $((d+4096)) --drafting off 2>&1 | grep -E 'generation:|error|die' | tail -1)
  echo "kv=$kv depth=$d $r"; done; done
journalctl -k --since "-10min" --no-pager | grep -c gfxhub
