#!/usr/bin/env bash
# ON the instance: idea.sh <name> <binA> "<envA>" <binB> "<envB>" — quick gate + ABBA for one idea (nv-3090,
# 2026-10-20). Arms on the T config (arm.sh N): A.p1 B.p1 (chat T=1 seeds 1,2 + chat T=0 + mvs) then B.p2 A.p2
# (chat T=1 seeds 3,4 + mvs). md5 per request lands in rows.jsonl: the gate is B rows == A rows for every common
# (set, prompt, temp, seed) key (ABBA_MD5 line). env strings are space-separated VAR=val ("" = none).
set -uo pipefail
name=$1; ba=$2; ea=$3; bb=$4; eb=$5
cd /root/cloud
export MODEL=${MODEL:-Qwen3.8-27B-UD-Q6_K_M.gguf} CTX=${CTX:-32768} CPUS=${CPUS:-0-5} OUT=/root/results/nv3090/logs
SEEDS=1,2 BIN=$ba ./arm.sh $name.A.p1 N chat1,chat0,mvs $ea
SEEDS=1,2 BIN=$bb ./arm.sh $name.B.p1 N chat1,chat0,mvs $eb
SEEDS=3,4 BIN=$bb ./arm.sh $name.B.p2 N chat1,mvs $eb
SEEDS=3,4 BIN=$ba ./arm.sh $name.A.p2 N chat1,mvs $ea
python3 - "$OUT/rows.jsonl" "$name" <<'EOF'
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1])]
n = sys.argv[2]
a = {(r["set"], r["prompt"], r["temp"], r["seed"]): r["md5"] for r in rows if r["label"].startswith(n + ".A.")}
b = {(r["set"], r["prompt"], r["temp"], r["seed"]): r["md5"] for r in rows if r["label"].startswith(n + ".B.")}
k = sorted(set(a) & set(b))
same = sum(a[x] == b[x] for x in k)
print(f"ABBA_MD5 {n}: {same}/{len(k)} identical" + ("" if same == len(k) else " DIFF: " + str([x for x in k if a[x] != b[x]][:6])))
EOF
