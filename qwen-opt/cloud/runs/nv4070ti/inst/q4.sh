#!/usr/bin/env bash
# ON the box: after q3 (q3.done): correctness of LLAMA_SPEC_COUPLED=1 on this card — test-backend-ops GUMBEL_MAX /
# TOP_K / GET_ROWS / SUM_ROWS (nv tree), md5 gates coupled with GPU verify on (TV=1) and off (TV=0).
set -uo pipefail
R=/root/results/opt-4070ti-20261020; G=$R/gate
while [ ! -f $R/q3.done ]; do sleep 10; done
cd /root/cloud
for op in GUMBEL_MAX TOP_K GET_ROWS SUM_ROWS; do
    taskset -c 6-11 /root/src/nv/b89/bin/test-backend-ops test -b CUDA0 -o $op > $G/tbo-$op.log 2>&1
    echo "tbo $op rc=$? $(grep -E 'tests passed' $G/tbo-$op.log | tail -1)"
done
TENV="LLAMA_SPEC_COUPLED=1" TV=1 ./gate.sh coupled
TENV="LLAMA_SPEC_COUPLED=1" TV=0 ./gate.sh coupledgv0
touch $R/q4.done
