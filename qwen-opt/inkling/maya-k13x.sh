#!/bin/bash
# K-136 / K-137 arms on XTX. Each arm: ~/k134/hipx/rep2.sh <tag> <config> (5-run medians Q1 / Q6 T=0.7 / L2k / prefill).
# Switches = production hipx14 set. KV q4 everywhere (owner rule). Usage: maya-k13x.sh test | run <arm>...
set -u
cd ~/k134
M=$HOME/models/inkling; TOK=$HOME/k134/maya/ik2/tokenizer
SW='"IK2_KV":"q4","IK2_HIP_COMB":"1","IK2_HIP_EXPV":"1","IK2_HIP_FUSE":"1","IK2_HIP_LGD":"2","IK2_HIP_LGR":"1","IK2_HIP_MVF16":"1","IK2_HIP_NT":"15","IK2_HIP_PCONV":"1"'
AB="\"IK2_ABLATE\":\"$M/Inkling-2-Mini-Uncensored-LoRA.gguf\","
cfg() {  # name exe model drafting-args env-extra
  printf '{"exe":"%s","args":["--model","%s","--max-context","16384"%s],"tokenizer":"%s","model_name":"inkling-2-mini","log":"%s/k134/%s.log","env":{"LD_LIBRARY_PATH":"/opt/rocm/core-10.0/lib",%s%s}}\n' \
    "$2" "$3" "$4" "$TOK" "$HOME" "$1" "$5" "$SW" > ~/k134/$1.json; }
P=$HOME/k134/maya/build-hip/maya-ik2.hipx14; N=$HOME/k134/wt-k175/build-hip/maya-ik2; Q=$HOME/k134/wt-ad-q4k/build-hip/maya-ik2; QN=$HOME/k134/wt-k175-ad/build-hip/maya-ik2
case ${1:-} in
  test) for b in wt-k175 wt-ad-q4k wt-k175-ad; do for e in "" "IK2_HIP_EXPV=1 IK2_HIP_NT=15"; do echo "== $b [$e]"; env LD_LIBRARY_PATH=/opt/rocm/core-10.0/lib $e timeout 180 ~/k134/$b/build-hip/ik2_kernels_test 2>&1 | grep -iE "fail|mismatch|off by|passed|error" | tail -6; done; done
        journalctl -k --since "-10min" --no-pager | grep -c gfxhub ;;
  run) shift
    cfg k136-prod    $P $M/Inkling-2-Mini-UD-Q4_K_XL.gguf ',"--drafting","on"' "$AB"
    cfg k136-175-on  $N $M/Inkling-2-Mini-UD-Q4_K_XL.gguf ',"--drafting","on"' "$AB"
    cfg k136-175-ds  $N $M/Inkling-2-Mini-UD-Q4_K_XL.gguf ",\"--draft\",\"$M/dspark-Inkling-2-Mini-Q8_0.gguf\",\"--drafting\",\"on\"" "$AB"
    cfg k136-175-dsa $N $M/Inkling-2-Mini-UD-Q4_K_XL.gguf ",\"--draft\",\"$M/dspark-Inkling-2-Mini-Q8_0.gguf\",\"--drafting\",\"auto\"" "$AB"
    cfg k137-ad      $Q $M/Inkling-2-Mini-Uncensored-AD-Q4_K.gguf ',"--drafting","on"' ""
    cfg k137-ad175   $QN $M/Inkling-2-Mini-Uncensored-AD-Q4_K.gguf ",\"--draft\",\"$M/dspark-Inkling-2-Mini-Q8_0.gguf\",\"--drafting\",\"auto\"" ""
    for a in "$@"; do ~/k134/hipx/rep2.sh $a ~/k134/$a.json; done ;;
esac
