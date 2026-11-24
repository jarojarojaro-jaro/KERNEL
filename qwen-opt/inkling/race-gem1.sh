#!/bin/bash
# Race round Gemini g1c (gem-maya 96f45fc): kernel tests with/without IK2_G_*, then rep2 arms (AtomicChat AD-Q4_K, KV q4).
# Baseline = production 113.2 (maya-atomic.json: 1.1.73 adq4k, lookup); same-session arm k175-ad lookup and DSpark.
set -u; cd ~/k134
M=$HOME/models/inkling; TOK=$HOME/k134/maya/ik2/tokenizer; X=$HOME/k134/wt-gem-maya/build-hip
SW='"IK2_KV":"q4","IK2_HIP_COMB":"1","IK2_HIP_EXPV":"1","IK2_HIP_FUSE":"1","IK2_HIP_LGD":"2","IK2_HIP_LGR":"1","IK2_HIP_MVF16":"1","IK2_HIP_NT":"15","IK2_HIP_PCONV":"1"'
G='"IK2_G_WEXP":"1","IK2_G_WCOLS":"1","IK2_G_WROUTE":"1","IK2_G_WLOOP":"1","IK2_G_DGRAPH":"1","IK2_G_DFAST":"1",'
GENV="IK2_G_WEXP=1 IK2_G_WCOLS=1 IK2_G_WROUTE=1 IK2_G_WLOOP=1 IK2_G_DGRAPH=1 IK2_G_DFAST=1"
cfg() { printf '{"exe":"%s","args":["--model","%s","--max-context","16384"%s],"tokenizer":"%s","model_name":"inkling-2-mini","log":"%s/k134/%s.log","env":{"LD_LIBRARY_PATH":"/opt/rocm/core-10.0/lib",%s%s}}\n' "$X/maya-ik2" "$M/Inkling-2-Mini-Uncensored-AD-Q4_K.gguf" "$2" "$TOK" "$HOME" "$1" "$3" "$SW" > ~/k134/$1.json; }
DS=",\"--draft\",\"$M/dspark-Inkling-2-Mini-Q8_0.gguf\",\"--drafting\",\"on\""
DA=",\"--draft\",\"$M/dspark-Inkling-2-Mini-Q8_0.gguf\",\"--drafting\",\"auto\""
case $1 in
  test) for e in "IK2_HIP_EXPV=1 IK2_HIP_NT=15 IK2_HIP_LGD=2 IK2_HIP_MVF16=1 IK2_HIP_FUSE=1 IK2_HIP_LGR=1" "IK2_HIP_EXPV=1 IK2_HIP_NT=15 IK2_HIP_LGD=2 IK2_HIP_MVF16=1 IK2_HIP_FUSE=1 IK2_HIP_LGR=1 $GENV"; do
          echo "== [$e]"; env LD_LIBRARY_PATH=/opt/rocm/core-10.0/lib $e timeout 280 $X/ik2_kernels_test > /tmp/g1-test.log 2>&1; echo rc=$?; grep -cE "^ok" /tmp/g1-test.log; grep -E "FAIL|passed" /tmp/g1-test.log | head -12; done
        journalctl -k --since "-6min" --no-pager | grep -c gfxhub ;;
  run) shift
    cfg g1-off-lk ',"--drafting","on"' ""; cfg g1-off-ds "$DS" ""; cfg g1-all-ds "$DS" "$G"; cfg g1-all-auto "$DA" "$G"; cfg g1-all-lk ',"--drafting","on"' "$G"
    for a in "$@"; do ~/k134/hipx/rep2.sh $a ~/k134/$a.json; done ;;
  parity) # greedy answers drafting off vs on with all IK2_G_* (gen.py, T=0): must be identical
    cfg g1-par-off ',"--drafting","off"' "$G"; cfg g1-par-ds "$DS" "$G"
    for a in g1-par-off g1-par-ds; do LD_LIBRARY_PATH=/opt/rocm/core-10.0/lib ./ablate/gen.sh $a ~/k134/$a.json > /dev/null 2>&1; done
    python3 -c "
import json; a=json.load(open('/home/jaro/k134/ablate/g1-par-off.json')); b=json.load(open('/home/jaro/k134/ablate/g1-par-ds.json'))
d=[k for k in a if a[k]['answer']!=b.get(k,{}).get('answer')]; print('parity', 'IDENTICAL' if not d else 'DIFF '+','.join(d), len(a))" ;;
esac
