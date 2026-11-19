#!/bin/bash
# K-109 + K-110 on the XTX (inside run-jobs.sh): production config (run-topka.sh uncensored, PM4 WA=2 GUARD, ctx 262144)
# on test port 18794. K-110: skill-io bench.py unchanged (T 0.6, c1 6x512, prefill 4k/16k). K-109: 3 needles at ~131k
# and ~223k tokens. Server stopped with ONE SIGTERM, 60 s, then SIGKILL. Results: ledger.jsonl + logs here.
set -u
cd ~/qwen-opt/k109
export PORT=18794 CTX=262144
unset QUEUE_PM4_SAFETY GGML_HIP_PM4   # production PM4 config from run-topka.sh (WA=2 GUARD=1), as on :8080
~/qwen-opt/run-topka.sh uncensored > server.log 2>&1 < /dev/null &
for _ in $(seq 300); do curl -sf 127.0.0.1:18794/health > /dev/null && break; sleep 1; done
curl -sf 127.0.0.1:18794/health > /dev/null || { echo "server not healthy"; tail -20 server.log; exit 1; }
p=$(pgrep -f "llama-server.*--port 18794( |$)")
echo "server pid $p up $(date +%T)"
case ${1:-all} in
  k110|all) python3 bench.py run k110.json --skip-cN --reps 6 ;;&
  k109a|all) python3 bench.py run k109.json --skip-cN --reps 1 --long "$(python3 calib.py 131072)" ;;&
  k109b|all) python3 bench.py run k109.json --skip-cN --reps 1 --long "$(python3 calib.py 223000)" ;;&
  k106) python3 k106.py ;;
esac
rocm-smi --showmemuse --showtemp 2>/dev/null | grep -E "VRAM%|junction" > vram-end.txt
kill -TERM $p; for _ in $(seq 60); do kill -0 $p 2>/dev/null || break; sleep 1; done; kill -KILL $p 2>/dev/null
echo "server stopped $(date +%T)"
