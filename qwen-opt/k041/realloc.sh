#!/usr/bin/env bash
# K-041: do MTP / W16 / catch-up width changes rebuild the PM4 tape or the graph during an agent-like replay?
# Production config on port 18794 + GGML_HIP_PM4_DEBUG=1 (logs every tape build to stderr), agentpath w6.json, 4 lanes
# served one after another (24 turns, 40k chars each, max 128 out, T=0). Tape builds during warm-up vs during the replay.
# Queue only.
set -u
export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0 GGML_HIP_PM4_DEBUG=1
P=18794; here=$(cd "$(dirname "$0")" && pwd); out=$here/out; rm -rf "$out"; mkdir -p "$out"; L=$out/launch.log  # PM4 debug goes to stderr = launch log
PORT=$P LOG=$out/server.log setsid ~/qwen-opt/run-topka.sh uncensored > "$L" 2>&1 &
srv=$!
trap 'kill -TERM -- -$srv 2>/dev/null; for _ in $(seq 30); do kill -0 $srv 2>/dev/null || break; sleep 1; done; kill -KILL -- -$srv 2>/dev/null' EXIT
for _ in $(seq 240); do curl -sf 127.0.0.1:$P/health > /dev/null && break; sleep 1; done
sleep 2
c0=$(grep -c 'ggml_hip_pm4: tape:' "$L"); f0=$(grep -c 'ggml_hip_pm4:' "$L"); l0=$(wc -l < "$L")
echo "after warm-up: tape builds $c0, all pm4 debug lines $f0"
cd ~/qwen-opt/agentpath && timeout 420 ~/qwen-opt/.venv/bin/python swarm_replay.py w6.json --port $P --label k041 --order serial --out "$out/replay.jsonl" | tail -2
c1=$(grep -c 'ggml_hip_pm4: tape:' "$L"); f1=$(grep -c 'ggml_hip_pm4:' "$L")
echo "during replay: tape builds $((c1 - c0)), other pm4 debug lines $((f1 - f0 - c1 + c0))"
echo "== tape builds during replay by size"; tail -n +$((l0 + 1)) "$L" | grep -o 'ggml_hip_pm4: tape: [0-9]* dispatches' | sort | uniq -c | sort -rn | head -20
echo "== other pm4 lines during replay"; tail -n +$((l0 + 1)) "$L" | grep 'ggml_hip_pm4:' | grep -v 'tape:' | sed 's/[0-9]\+/N/g' | sort | uniq -c | sort -rn | head -10
echo "== warm-up tape builds by size"; head -n $l0 "$L" | grep -o 'ggml_hip_pm4: tape: [0-9]* dispatches' | sort | uniq -c | sort -rn | head -20
echo "== spec stats"; grep -E 'print_stats|draft acceptance' "$out/server.log" | tail -3
