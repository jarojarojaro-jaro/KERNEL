#!/bin/bash
# K-146: drafter for greedy only (IK2_K_DRAFT_T0) + lazy drafter context + DPP, vs production (adq4k-dpp, lookup)
set -u; cd ~/k134
M=$HOME/models/inkling; TOK=$HOME/k134/maya/ik2/tokenizer; X=$HOME/k134/wt-k175-lazy/build-hip/maya-ik2; AD=$M/Inkling-2-Mini-Uncensored-AD-Q4_K.gguf
SW='"IK2_KV":"q4","IK2_HIP_COMB":"1","IK2_HIP_EXPV":"1","IK2_HIP_FUSE":"1","IK2_HIP_LGD":"2","IK2_HIP_LGR":"1","IK2_HIP_MVF16":"1","IK2_HIP_NT":"15","IK2_HIP_PCONV":"1"'
cfg() { printf '{"exe":"%s","args":["--model","%s","--max-context","16384"%s],"tokenizer":"%s","model_name":"inkling-2-mini","log":"%s/k134/%s.log","env":{"LD_LIBRARY_PATH":"/opt/rocm/core-10.0/lib",%s%s}}\n' "$X" "$AD" "$2" "$TOK" "$HOME" "$1" "$3" "$SW" > ~/k134/$1.json; }
DR=",\"--draft\",\"$M/dspark-Inkling-2-Mini-Q8_0.gguf\",\"--drafting\",\"on\""
cfg k146-t0 "$DR" '"IK2_K_LAZYCTX":"1","IK2_K_DRAFT_T0":"1",'
case $1 in
  run) shift; for a in "$@"; do c=~/k134/$a.json; [ $a = prod ] && c=~/k134/maya-atomic.json; ~/k134/hipx/rep2.sh k146-$a-$RANDOM $c | grep "decode median"; done ;;
  parity) for a in k146-t0; do LD_LIBRARY_PATH=/opt/rocm/core-10.0/lib ./ablate/gen.sh p-$a ~/k134/$a.json > /dev/null 2>&1; done
    LD_LIBRARY_PATH=/opt/rocm/core-10.0/lib ./ablate/gen.sh p-k146-prod ~/k134/maya-atomic.json > /dev/null 2>&1
    python3 -c "
import json; a=json.load(open('/home/jaro/k134/ablate/p-k146-prod.json')); b=json.load(open('/home/jaro/k134/ablate/p-k146-t0.json'))
d=[k for k in a if a[k]['answer']!=b.get(k,{}).get('answer')]; print('parity prod vs t0:', 'IDENTICAL' if not d else 'DIFF '+','.join(d), len(a))" ;;
esac
