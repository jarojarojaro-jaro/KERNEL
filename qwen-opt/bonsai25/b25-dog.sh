#!/usr/bin/env bash
# DogukanUrker 3060 config (X 2026-11-24: 262K, ~74 tok/s with MTP, 47 without) reproduced on XTX: decode t/s of
# 5 chat answers at temp 1.0 / top-p 0.95 / top-k 20, 400 tokens, thinking off. usage: b25-dog.sh ENGINE MODEL [extra args]
set -uo pipefail
eng=$1 mod=$2; shift 2
case $eng in prism) B=$HOME/wt/prism/build-hip/bin;; topka) B=$HOME/wt/topka-bonsai/build-hip/bin;; *) B=$eng;; esac
M=$HOME/models/bonsai25/Ternary-Bonsai-2.5-27B-Uncensored-$mod-mtp.gguf; PORT=18796
export LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib
if [ "${PM4:-0}" = 1 ]; then export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0; else export GGML_HIP_PM4=0; fi
~/qwen-opt/l1tok/chat8080.sh stop
taskset -c 2-5 $B/llama-server -m $M -ngl 999 -c 262144 -fa on --jinja -np 1 -ctk q4_0 -ctv q4_0 -ctkd q4_0 -ctvd q4_0 \
  -b 1024 -ub 256 --spec-type draft-mtp --spec-draft-n-min 0 --spec-draft-n-max 3 --spec-draft-p-min 0 \
  --host 127.0.0.1 --port $PORT "$@" > /tmp/b25-dog.log 2>&1 & srv=$!
trap 'kill -TERM $srv 2>/dev/null; sleep 3; kill -9 $srv 2>/dev/null' EXIT
for _ in $(seq 300); do curl -sf 127.0.0.1:$PORT/health >/dev/null && break; sleep 1; done
python3 - $PORT "$eng-$mod${PM4:+-pm4}$*" <<'PY'
import json,sys,urllib.request,statistics
port,tag=sys.argv[1],sys.argv[2]
P=["Explain how a B-tree index works in a database, with an example.","Write a Python function that parses ISO 8601 dates, with tests.",
   "Tell me a short story about a lighthouse keeper.","What are the main causes of the French Revolution?","Napisz po polsku krótki poradnik parzenia kawy w ekspresie przelewowym."]
r=[]
for p in P:
    b={"messages":[{"role":"user","content":p}],"max_tokens":400,"temperature":1.0,"top_p":0.95,"top_k":20,"min_p":0.0,"seed":1,"chat_template_kwargs":{"enable_thinking":False}}
    t=json.load(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",data=json.dumps(b).encode(),headers={"Content-Type":"application/json"}),timeout=600))["timings"]
    r.append(t["predicted_per_second"])
print(f"DOG {tag}: temp 1.0 decode median {statistics.median(r):.1f} t/s runs {[round(x,1) for x in r]}")
PY
