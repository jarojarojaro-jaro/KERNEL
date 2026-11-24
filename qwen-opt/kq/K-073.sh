#!/usr/bin/env bash
# K-073: Flint (NVFP4) needle on XTX — is the empty 150k answer a token limit (model still thinking) or a long-context bug?
# Uses ~/qwen-opt/flint/fl_correct.py needle (gen 4096; records finish_reason, secret_in_reasoning, reasoning tail).
# Test port 18794 (never 8080), server + client under taskset -c 2-5, PM4=0 rule set explicitly.
# usage: K-073.sh BIN LABEL KV CTX SIZES   BIN: flint/inst/bin (now) or flint/base-inst/bin (upstream+PR); SIZES e.g. 150000,65536
set -uo pipefail
BIN=$1; LABEL=$2; KV=$3; CTX=$4; SIZES=$5
export GGML_HIP_PM4=0
FL=$HOME/qwen-opt/flint; PORT=18794
out=$(cd "$(dirname "$0")" && pwd)/out; mkdir -p "$out"
lab=$LABEL-$KV-c$CTX
~/qwen-opt/l1tok/chat8080.sh stop
"$HOME/qwen-opt/lookup/vram_ok.sh" || exit 1
taskset -c 2-5 "$BIN/llama-server" -m "$HOME/models/flint/flint-nvfp4.gguf" -ngl 99 -fa on -ctk "$KV" -ctv "$KV" -c "$CTX" \
    -ub 1024 -b 2048 -np 1 --jinja --host 127.0.0.1 --port $PORT > "$out/K-073-$lab.server.log" 2>&1 &
srv=$!
stop() {
    for _ in $(seq 60); do curl -s -m 2 "127.0.0.1:$PORT/slots" 2>/dev/null | grep -q '"is_processing":true' || break; sleep 1; done
    kill -TERM $srv 2>/dev/null
    for _ in $(seq 45); do kill -0 $srv 2>/dev/null || break; sleep 1; done
    kill -9 $srv 2>/dev/null; wait $srv 2>/dev/null
}
trap stop EXIT
trap 'exit 1' TERM INT
for _ in $(seq 300); do
    curl -sf "127.0.0.1:$PORT/health" >/dev/null && break
    kill -0 $srv 2>/dev/null || { echo "$lab: server exited"; tail -5 "$out/K-073-$lab.server.log"; exit 1; }
    sleep 1
done
rc=0
for s in ${SIZES//,/ }; do
    taskset -c 2-5 timeout 400 python3 "$FL/fl_correct.py" needle --port $PORT --size "$s" --gen 4096 --label "$lab" \
        --out "$out/K-073.jsonl" > /dev/null || rc=1
done
grep "\"$lab\"" "$out/K-073.jsonl" | jq -c '{label, size, prompt_n, ok, secret_in_reasoning, finish, tg_n, tg_ts, wall_s}'
exit $rc
