#!/usr/bin/env bash
# K-060 P0: factory re-verify of claim 2026-10-17-mmq-epi-0070 (GGML_HIP_MMQ_EPI 0 vs 1, build ~/llama-opt, sha256 still matches).
# The 2026-10-19 run was VOID only because gate H8 saw :8080 up, so :8080 is stopped first (restore = last job of K-060.jobs).
# PM4 rule: factory gate H2 forces GGML_HIP_PM4=0 in every block; exported here too. Test port 18450 (factory range 18434-18499), taskset -c 2-5.
# usage: K-060.sh ROUNDS   (one verify per job; each job = its own ledger row)
set -u
rounds=${1:-1}
export GGML_HIP_PM4=0
~/qwen-opt/l1tok/chat8080.sh stop
cd ~/qwen-opt/factory || exit 1
taskset -c 2-5 ./factory verify claims/2026-10-17-mmq-epi-0070.json --rounds "$rounds" --port 18450 --pause 20
rc=$?
grep 2026-10-17-mmq-epi-0070 ledger.jsonl | tail -1 | \
  jq -c '{claim_id, verdict, void_reason, effect: .effect_pct, ci95, median: .aa.median, ts}'
exit $rc
