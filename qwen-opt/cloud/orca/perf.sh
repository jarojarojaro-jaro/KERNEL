#!/usr/bin/env bash
# Isolated GPU kernel timings (test-backend-ops perf) for the Orca quant mix.
# Variants are run interleaved twice and we keep the faster run per case, which is robust against the
# clock/host drift seen on shared Vast boxes.
set -u
B=/root/w/fork/build/bin
export LD_LIBRARY_PATH=$B
OUT=${OUT:-/root/perf}
mkdir -p "$OUT"
run() {  # name env... -- filter
    local name=$1 filter=$2; shift 2
    env "$@" $B/test-backend-ops perf -o MUL_MAT -b CUDA0 -p "$filter" > "$OUT/$name.txt" 2>&1
}
run_fa() {  # name filter
    local name=$1 filter=$2
    $B/test-backend-ops perf -o FLASH_ATTN_EXT -b CUDA0 -p "$filter" > "$OUT/$name.txt" 2>&1
}

for round in 1 2; do
    run n1_rows0_r$round "type_a=iq4_xs,n=1" GGML_CUDA_MMVQ_N1_ROWS=0
    run n1_rows2_r$round "type_a=iq4_xs,n=1" GGML_CUDA_MMVQ_N1_ROWS=2
    run n1_rows4_r$round "type_a=iq4_xs,n=1" GGML_CUDA_MMVQ_N1_ROWS=4
    run n3_mrows0_r$round "type_a=iq4_xs,n=3" GGML_CUDA_MMVQ_MROWS=0
    run n3_mrows4_r$round "type_a=iq4_xs,n=3" GGML_CUDA_MMVQ_MROWS=4
    run q4k_n1_r$round   "type_a=q4_k,n=1"
    run q4_0_n1_r$round  "type_a=q4_0,n=1"
done
# FA: the model's geometry is D=256, n_head=24, n_head_kv=4
run_fa fa_q4_0 "type_K=q4_0,type_V=q4_0"
run_fa fa_f16  "type_K=f16,type_V=f16"
run_fa fa_q8_0 "type_K=q8_0,type_V=q8_0"
echo "perf done -> $OUT"
