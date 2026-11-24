#!/bin/bash
# K-147: IK2_SUFFIX=128 (wide suffix verify, ported from GodGMN f472e94) on production ad-dpp: parity, rep2, copy/edit
set -u; cd ~/k134
python3 - <<'PY'
import json; c=json.load(open('/home/jaro/k134/maya-atomic.json'))
c['exe']='/home/jaro/k134/wt-ad-suffix/build-hip/maya-ik2'; c['env']['IK2_SUFFIX']='128'; c['log']='/home/jaro/k134/k147-sfx.log'
json.dump(c,open('/home/jaro/k134/k147-sfx.json','w'))
PY
case $1 in
  run) shift; for a in "$@"; do c=~/k134/k147-sfx.json; [ $a = prod ] && c=~/k134/maya-atomic.json; ~/k134/hipx/rep2.sh k147-$a-$RANDOM $c | grep "decode median"; done ;;
  parity) LD_LIBRARY_PATH=/opt/rocm/core-10.0/lib ./ablate/gen.sh p-k147-prod ~/k134/maya-atomic.json > /dev/null 2>&1
    LD_LIBRARY_PATH=/opt/rocm/core-10.0/lib ./ablate/gen.sh p-k147-sfx ~/k134/k147-sfx.json > /dev/null 2>&1
    python3 -c "
import json; a=json.load(open('/home/jaro/k134/ablate/p-k147-prod.json')); b=json.load(open('/home/jaro/k134/ablate/p-k147-sfx.json'))
d=[k for k in a if a[k]['answer']!=b.get(k,{}).get('answer')]; print('parity prod vs suffix128:', 'IDENTICAL' if not d else 'DIFF '+','.join(d), len(a))"
    grep -h "suffix:" ~/k134/k147-sfx.log | tail -3 ;;
  copy) ARMS="ours-lookup ours-suffix128 ours-lookup ours-suffix128" ~/k141/k141.sh copy ;;
esac
