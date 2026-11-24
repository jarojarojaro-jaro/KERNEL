#!/bin/bash
# K-141 / K-144: our Maya (AtomicChat AD-Q4_K, adq4k, production env) vs GodGMN hip-port f472e94 (Victor's release binary,
# ggml-org IQ4_NL; equal bytes/token) through the same harness (GodGMN tools/ik2_bench.py, --serve-ik2 GEN protocol).
#   bench <greedy|t07>  depths 512,2048,8192, gen 129, repeats 3, chunk 1024
#   copy                tests/ik2_copy_edit.py (copy + edit, direct answer): ours lookup vs theirs default vs IK2_SUFFIX=128
set -u
G=$HOME/k141/godgmn; PY=$HOME/qwen-opt/mtp-train/.venv/bin/python
OURS=$HOME/k134/maya/build-hip/maya-ik2.adq4k-dpp; THEIRS=$HOME/k141/godgmn/build-hip/maya-ik2
AD=$HOME/models/inkling/Inkling-2-Mini-Uncensored-AD-Q4_K.gguf; NL=$HOME/models/inkling/Inkling-2-Mini-IQ4_NL.gguf
export LD_LIBRARY_PATH=/opt/rocm/core-10.0/lib ROCBLAS_TENSILE_LIBPATH=/opt/rocm/core-10.0/lib/rocblas/library
TENV="IK2_HOST=mmap IK2_KV=fp8 IK2_GATE_TILE=256 IK2_GATE_BF16=1 IK2_Q8_UNROLL=1 IK2_BATCH_PREFILL=1 IK2_PREFILL_WMMA=1 IK2_PREFILL_TILE=auto IK2_PREFILL_SWIGLU=1 IK2_EXPERT_TILE_LDS=1 IK2_PREFILL_DENSE=2 IK2_FLASH=1 IK2_FLASH_WAVES=4 IK2_DENSE_WMMA=1 IK2_DECODE_SUBWAVE=1 IK2_ATTN_MMA=3 IK2_GRAPH_PAIR=1 IK2_ATTN_STAGED=1 IK2_SHARED_COMBINE=1 IK2_RESIDENT_ONLY=1 IK2_EXPERT_LIMB=0 IK2_F16_MV=2 IK2_IQ4_MV=1 IK2_Q8_MV=1 IK2_DECODE_PROJ=1 IK2_Q8_TILE=1"   # GodGMN preset docs/inkling2-mini/ik2-mini-gfx1100.json
OENV="IK2_KV=q4 IK2_HIP_COMB=1 IK2_HIP_EXPV=1 IK2_HIP_FUSE=1 IK2_HIP_LGD=2 IK2_HIP_LGR=1 IK2_HIP_MVF16=1 IK2_HIP_NT=15 IK2_HIP_PCONV=1"
TOK=$HOME/k141/bench.tok; [ -f $TOK ] || cp $HOME/k134/hipx/short.tok $TOK
summ() { python3 -c "
import json,sys,statistics as st,collections as C
d=C.defaultdict(lambda: [[],[]])
for l in sys.stdin:
    try: r=json.loads(l)
    except: continue
    if 'depth' in r: d[r['depth']][0].append(r['decode_tok_s']); d[r['depth']][1].append(r['prefill_tok_s'])
for k in sorted(d): print(f'  depth {k}: decode {st.median(d[k][0]):.1f} t/s, prefill {st.median(d[k][1]):.0f} t/s')"; }
case $1 in
  bench) T=0; P=1; [ "${2:-greedy}" = t07 ] && T=0.7 P=0.95
    for arm in ours theirs ours theirs; do
      if [ $arm = ours ]; then e="$OENV"; b=$OURS; m=$AD; else e="$TENV"; b=$THEIRS; m=$NL; fi
      echo "== $arm T=$T"; (cd $G && env $e timeout 400 taskset -c 2-5 $PY tools/ik2_bench.py --engine $b --model $m --tokens $TOK --depths 512,2048,8192 --gen 129 --repeats 3 --chunk 1024 --ctx 16384 --temperature $T --top-p $P 2>&1 | tee /tmp/k141-$arm.jsonl | summ; grep -iE "error|die|abort" /tmp/k141-$arm.jsonl | head -3)
    done ;;
  copy) cd $G/tests
    $PY ik2_copy_edit.py --tokenizer $HOME/k134/maya/ik2/tokenizer --direct-answer --workload inventory > /tmp/k144-req.txt
    for arm in ours-lookup theirs-default theirs-suffix128; do
      case $arm in ours-lookup) e="$OENV"; b="$OURS --drafting on"; m=$AD;; theirs-default) e="$TENV"; b=$THEIRS; m=$NL;; theirs-suffix128) e="$TENV IK2_SUFFIX=128"; b=$THEIRS; m=$NL;; esac
      env $e timeout 400 taskset -c 2-5 $b --model $m --serve-ik2 --ctx 16384 --chunk 1024 < /tmp/k144-req.txt > /tmp/k144-$arm.out 2>/tmp/k144-$arm.err
      echo "== $arm"; $PY ik2_copy_edit.py --tokenizer $HOME/k134/maya/ik2/tokenizer --direct-answer --workload inventory --score /tmp/k144-$arm.out 2>&1 | cut -c1-220; tail -2 /tmp/k144-$arm.err
    done ;;
esac
journalctl -k --since "-10min" --no-pager | grep -c gfxhub
