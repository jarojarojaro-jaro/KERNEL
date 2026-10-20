#!/usr/bin/env bash
# ON the box: ab.sh <name> "<TENV A>" "<TENV B>" [TK_A] [TK_B] — short ABBA of two T configs, fresh server per pass:
# chat T=1 (spec_sweep 6 prompts x seeds ${SEEDS:-1,2}, 400 tok) + mvs T=0 (copy_bench, 1024 tok).
# Labels ab.<name>.<A|B>.p<1..4>; rows in logs/spec_sweep.jsonl and logs/copy_bench.jsonl. NMAX/CTX from env;
# XA / XB: extra llama-server args of arm A / B (appended last, so they override, e.g. XB="--spec-draft-n-max 3").
set -uo pipefail
. /root/cloud/lib4070.sh
name=$1; EA=$2; EB=$3; KA=${4:-$TK}; KB=${5:-$TK}
i=0
for x in A B B A; do
    i=$((i + 1)); label=ab.$name.$x.p$i
    if [ $x = A ]; then TENV=$EA; TK=$KA; TARGS=${XA:-}; else TENV=$EB; TK=$KB; TARGS=${XB:-}; fi
    say "$label TENV='$TENV' TARGS='$TARGS' TK=$TK"
    srv T "$L/$label.server.log" || { say "$label failed"; tail -5 "$L/$label.server.log"; exit 1; }
    sleep 2; vram_row "$label" ""
    (cd "$L" && $BC python3 $H/spec_sweep.py --label "$label" --port $PORT --temps 1.0 --seeds "${SEEDS:-1,2}" --tokens 400)
    $BC python3 $H/copy_bench.py --label "$label" --port $PORT --set mvs --temps 0.0 --tokens 1024 --out "$L/copy_bench.jsonl"
    srv_stop
done
say "ab $name done"
