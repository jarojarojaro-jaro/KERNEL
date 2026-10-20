#!/usr/bin/env bash
# ON the box: mb.sh <tree> "<env cfg 1>" "<env cfg 2>" ... — test-backend-ops correctness (MUL_MAT, CUDA0 vs CPU) and
# perf (m=4096, k=14336, n=1 and n=5) of the verify types for each env config, in order cfg1 cfg2 ... cfg1 (A..A).
# "-" = no extra env. Output: logs/mb.<tree>.jsonl-ish text in logs/mb.<tree>.txt
set -uo pipefail
. /root/cloud/lib4070.sh
t=$1; shift
B=$S/$t/b89/bin; out=$L/mb.$t.txt
re='type_a=(iq3_xxs|iq3_s|iq2_s|iq2_xxs|iq2_xs|iq1_s|iq4_xs|q4_K),type_b=f32,m=4096,n=(1|5),k=14336'
cfgs=("$@" "$1")
for c in "${cfgs[@]}"; do
    e=""; [ "$c" != "-" ] && e=$c
    echo "### cfg '$e' $(date +%T)" >> "$out"
    lg="$L/mb.$t.tbo.$(echo "$e" | tr ' =' '__').log"
    env $e $BC $B/test-backend-ops test -b CUDA0 -o MUL_MAT -p 'type_a=(iq|q[2-6]_K)' > "$lg" 2>&1
    echo "tbo rc=$? $(grep -E 'tests passed' "$lg" | tail -1)" >> "$out"
    env $e $BC $B/test-backend-ops perf -b CUDA0 -o MUL_MAT -p "$re" 2>&1 | grep -E "MUL_MAT" >> "$out"
done
cat "$out"
