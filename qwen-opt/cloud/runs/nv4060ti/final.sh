#!/usr/bin/env bash
# ON the box (report 31): final before/after on Qwen3.8-27B UD-IQ4_XS, KV q4_0, -c $C, arms U0 U1 T T' (T' = X with
# XBIN/XENV). Order: gate T' (md5 GV=0 vs GV=1), llama-bench U T X X T U, pass 1 U0 U1 T X (full: sweep 6x3 + mvs +
# long 512/16k), pass 2 X T U1 U0 (sweep 6x3). Same harness as nv.sh (fresh server per arm, taskset 0-2,6-8).
set -uo pipefail
cd /root
export C=${C:-40960}
: "${XBIN:?}" "${XENV:?}"
say() { echo "=== $(date +%T) $*"; }
say "final: C=$C XBIN=$XBIN XENV=$XENV"
GV0ENV="${XENV/LLAMA_GPU_VERIFY=1/} LLAMA_GPU_VERIFY=0"
./nv.sh gate gate.TP.gv1
XENV="$GV0ENV" ./nv.sh gate gate.TP.gv0
cmp -s res/gate/md5.gate.TP.gv1.txt res/gate/md5.gate.TP.gv0.txt && say "gate TP: GV0 == GV1" || say "gate TP: GV0 != GV1 (see diff)"
diff res/gate/md5.gate.TP.gv0.txt res/gate/md5.gate.TP.gv1.txt > res/gate/md5.TP.diff
./nv.sh lb final U T X X T U
for a in U0 U1 T X; do ./nv.sh full $a 1; done
for a in X T U1 U0; do ./nv.sh full $a 2; done
touch res/final.done; say "final done"
