#!/usr/bin/env bash
# Report 37 items #3/#1: timing-only upper bounds on the 5-row verify-shaped batch (llama-bench pp5, Qwen UD-Q4_K_XL,
# FA, KV q4_0, PM4 WA=2 + GUARD, HSA_USE_SVM=0), fresh process per arm, order A B C ... C B A. The UB switches give
# WRONG OUTPUT (nothing is generated here, only the time of the 5-token batch is read).
#   base   switches off
#   skipn  GGML_HIP_UB_SKIP_NORM=1     the rms_norm*mul(+q8_1) launches of the batch are skipped (norm fusion bound)
#   ubm    GGML_HIP_PM4_UB=mmvq        no boundary before any MMVQ of the verify tape (dataflow stage 1 bound)
#   ubn    GGML_HIP_PM4_UB=norm        no boundary before any rms_norm* kernel
# usage: ub_bench.sh BIN_DIR [ARMS...]   Run ONLY from the GPU queue.
set -uo pipefail
bin=$1; shift
[ -x "$bin/llama-bench" ] || bin=$bin/bin
arms=("$@"); [ ${#arms[@]} -gt 0 ] || arms=(base skipn ubm ubn)
export LD_LIBRARY_PATH=$bin:/opt/rocm/core-10.0/lib
export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0
pkill -f 'llama-topka/bin/llama-server' && sleep 5
"$HOME/qwen-opt/lookup/vram_ok.sh" || exit 1
order=("${arms[@]}"); for ((i = ${#arms[@]} - 1; i >= 0; i--)); do order+=("${arms[i]}"); done
for a in "${order[@]}"; do
    case $a in
        base)  e=() ;;
        skipn) e=(GGML_HIP_UB_SKIP_NORM=1) ;;
        ubm)   e=(GGML_HIP_PM4_UB=mmvq) ;;
        ubn)   e=(GGML_HIP_PM4_UB=norm) ;;
        ubmn)  e=(GGML_HIP_PM4_UB=mmvq,norm) ;;
        *) echo "unknown arm $a"; exit 2 ;;
    esac
    r=$(env "${e[@]}" taskset -c 2-5 "$bin/llama-bench" -m "$HOME/models/Qwen3.8-27B-UD-Q4_K_XL.gguf" -ngl 99 -fa 1 \
        -ctk q4_0 -ctv q4_0 -p 5 -n 0 -r 200 -o jsonl 2> "/tmp/ub-$a.err" |
        python3 -c 'import json,sys; d=json.loads(sys.stdin.readline()); a=d["avg_ts"]; s=d["stddev_ts"]; print(f"{5000/a:.4f} ms/batch  {a:.2f} t/s  sd {s:.2f}")')
    echo "$a ${e[*]:-}: $r  $(grep -m1 -o 'GGML_HIP_PM4_UB dropped.*' "/tmp/ub-$a.err")"
done
