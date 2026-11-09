#!/bin/bash
# xtxbench t1 validation (queue job, XtxBench 2026-11-08). Run ONLY from ~/qwen-opt/queue/run-jobs.sh validate.jobs.
# 1. A/A on production (~/llama-topka, run-topka.sh uncensored, eco 2200): B on its own server (cross-process restore),
#    first run = snapshot creation 1.7k/94k/199k + md5 restore proof (fresh prefill+decode vs restore+decode vs one cold
#    request), noise pair A0', then the adaptive A -> B (+ B -> A if ambiguous). Every stage is timed (timings.jsonl).
# 2. Only if the hook build ~/wt/xtxbench/build-hip exists and is fresh: runtime switch smoke on ONE server
#    (GGML_HIP_MMVQ_PAIR=0 via GGML_HIP_RUNTIME_SWITCH_FILE: flip confirmed by the server, md5 must stay identical).
# xtxbench itself stops :8080 (ONE SIGTERM, 60 s, SIGKILL) and restores run-topka.sh uncensored on exit.
set -u
cd ~/qwen-opt/xtxbench || exit 1
py=~/qwen-opt/.venv/bin/python
$py xtxbench.py t1 --label aa-validate --force-restart --aa --renoise
rc=$?
H=~/wt/xtxbench/build-hip
if [ -x $H/bin/llama-server ] && $py xtxbench.py check --base $H > /dev/null 2>&1; then
  $py xtxbench.py t1 --label hook-mmvq-pair --base $H --var-switch GGML_HIP_MMVQ_PAIR=0 --snap-compat --renoise --t0 none || rc=$((rc ? rc : 4))
else
  echo "hook smoke skipped: $H not built (or stale)"
fi
exit $rc
