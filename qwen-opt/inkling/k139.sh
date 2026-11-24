#!/bin/bash
# K-139: Inkling speculation economics on XTX (Maya 1.1.75 + hipx14 + Q4_K/Q5_0 = wt-k175-ad, AtomicChat AD-Q4_K, KV q4)
#   run <arm>...  rep2 (Q1/Q6 T=0.7/L2k) per arm; STAT lines of each arm in ~/k134/k139-<arm>.log
#   trace         IK2_TRACE of 256 decode tokens (CLI) -> ~/k134/k139-route.trace (+ route_locality.py)
#   parity        greedy answers (gen.py) drafting off vs DSpark forced: identical?
set -u; cd ~/k134
M=$HOME/models/inkling; TOK=$HOME/k134/maya/ik2/tokenizer; X=$HOME/k134/wt-k175-ad/build-hip/maya-ik2; AD=$M/Inkling-2-Mini-Uncensored-AD-Q4_K.gguf
SW='"IK2_KV":"q4","IK2_HIP_COMB":"1","IK2_HIP_EXPV":"1","IK2_HIP_FUSE":"1","IK2_HIP_LGD":"2","IK2_HIP_LGR":"1","IK2_HIP_MVF16":"1","IK2_HIP_NT":"15","IK2_HIP_PCONV":"1","IK2_STATS":"1"'
cfg() { printf '{"exe":"%s","args":["--model","%s","--max-context","16384"%s],"tokenizer":"%s","model_name":"inkling-2-mini","log":"%s/k134/%s.log","env":{"LD_LIBRARY_PATH":"/opt/rocm/core-10.0/lib",%s%s}}\n' "$X" "$AD" "$2" "$TOK" "$HOME" "$1" "$3" "$SW" > ~/k134/$1.json; }
DR=",\"--draft\",\"$M/dspark-Inkling-2-Mini-Q8_0.gguf\""
case $1 in
  run) shift
    cfg k139-off ',"--drafting","off"' ""
    cfg k139-lk ',"--drafting","on"' ""
    cfg k139-auto "$DR,\"--drafting\",\"auto\"" '"IK2_DRAFT_MEASURE":"1",'
    cfg k139-dsadapt "$DR,\"--drafting\",\"on\"" '"IK2_LOOKUP":"0",'
    for w in 2 3 4 5 6 8; do cfg k139-ds$w "$DR,\"--drafting\",\"on\"" "\"IK2_LOOKUP\":\"0\",\"IK2_DRAFT_ADAPT\":\"0\",\"IK2_DRAFT_WIDTH\":\"$w\","; done
    cfg k139-lkdsload "$DR,\"--drafting\",\"on\"" '"IK2_DRAFT_WIDTH":"2",'   # drafter loaded; tax on plain steps
    for a in "$@"; do ~/k134/hipx/rep2.sh $a ~/k134/$a.json; echo "STAT $a: $(grep -E 'STAT draft|measured this PC' ~/k134/$a.log ~/k134/hipx/$a-server.log 2>/dev/null | tail -2 | cut -c1-230)"; done ;;
  trace) LD_LIBRARY_PATH=/opt/rocm/core-10.0/lib IK2_KV=q4 IK2_TRACE=$HOME/k134/k139-route.trace timeout 300 taskset -c 2-5 $X --model $AD --tokens @$HOME/k134/hipx/short.tok --gen 256 --ctx 4096 --drafting off 2>&1 | grep -E 'generation:|error' | tail -2
         ls -la ~/k134/k139-route.trace; python3 ~/k134/route_locality.py ~/k134/k139-route.trace 2>&1 | tail -25 ;;
  parity) cfg k139-par-off ',"--drafting","off"' ""; cfg k139-par-ds "$DR,\"--drafting\",\"on\"" '"IK2_LOOKUP":"0",'
    for a in k139-par-off k139-par-ds; do LD_LIBRARY_PATH=/opt/rocm/core-10.0/lib ./ablate/gen.sh $a ~/k134/$a.json > /dev/null 2>&1; done
    python3 -c "
import json; a=json.load(open('/home/jaro/k134/ablate/k139-par-off.json')); b=json.load(open('/home/jaro/k134/ablate/k139-par-ds.json'))
d=[k for k in a if a[k]['answer']!=b.get(k,{}).get('answer')]; print('parity drafting off vs DSpark:', 'IDENTICAL' if not d else 'DIFF '+','.join(d), len(a))" ;;
esac
