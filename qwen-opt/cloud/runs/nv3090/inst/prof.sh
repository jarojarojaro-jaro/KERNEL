#!/usr/bin/env bash
# ON the instance: prof.sh <label> <bin> <set:chat|mvs> [VAR=val ...] — nsys trace (cuda+osrt+nvtx, graph nodes) of
# one T-config server on /root/bin/<bin>: load outside the capture, then capture 1 warmup + 2 requests
# (chat: en-tech, pl-proza T=1 s1; mvs: first 2 prompts T=0). Out: /root/results/nv3090/prof/<label>.nsys-rep + stats.
set -uo pipefail
label=$1; bin=$2; set=$3; shift 3
H=/root/cloud; P=/root/results/nv3090/prof; PORT=18701; mkdir -p $P
MODEL=${MODEL:?}; CTX=${CTX:?}; CPUS=${CPUS:-0-7}
sess=s$$
taskset -c "$CPUS" nsys launch --session-new=$sess --trace=cuda,nvtx,osrt --cuda-graph-trace=${GT:-node} \
  env LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_SERVER_CACHE_SHARE_MIN=1024 LLAMA_GPU_VERIFY=${TV:-1} \
  LLAMA_SERVER_REASONING_CONTROL=0 "$@" /root/bin/$bin/llama-server -m /root/models/$MODEL -ngl 999 -fa on \
  -ctk q4_0 -ctv q4_0 -c $CTX -np 1 --jinja --cache-ram 16384 --reasoning-effort low --host 127.0.0.1 --port $PORT \
  --no-webui --spec-type draft-mtp --spec-draft-n-max 4 -ctkd q4_0 -ctvd q4_0 \
  --spec-draft-vocab $H/draft_vocab_qwen38.txt --spec-draft-vocab-n 65536 --spec-draft-head-type iq4_xs \
  --spec-mtp-type iq4_xs > $P/$label.server.log 2>&1 &
for _ in $(seq 600); do curl -sf http://127.0.0.1:$PORT/health > /dev/null && break; sleep 1; done
cd $H
python3 - <<EOF
import json, urllib.request
def chat(p, t, temp, copy):
    b = {"messages":[{"role":"user","content":p}],"max_tokens":t,"temperature":temp,"seed":1,"cache_prompt":copy}
    if copy: b["chat_template_kwargs"]={"enable_thinking":False}
    r = urllib.request.Request("http://127.0.0.1:$PORT/v1/chat/completions", data=json.dumps(b).encode(), headers={"Content-Type":"application/json"})
    return json.load(urllib.request.urlopen(r, timeout=900))["timings"]
chat("Hi", 16, 0.0, False)
EOF
nsys start --session=$sess -o $P/$label --force-overwrite=true
python3 - <<EOF
import json, urllib.request
from spec_sweep import PROMPTS
def chat(p, t, temp, copy):
    b = {"messages":[{"role":"user","content":p}],"max_tokens":t,"temperature":temp,"seed":1,"cache_prompt":copy}
    if copy: b["chat_template_kwargs"]={"enable_thinking":False}
    r = urllib.request.Request("http://127.0.0.1:$PORT/v1/chat/completions", data=json.dumps(b).encode(), headers={"Content-Type":"application/json"})
    return json.load(urllib.request.urlopen(r, timeout=900))["timings"]
if "$set" == "chat":
    for k in ("en-tech", "pl-proza"):
        t = chat(PROMPTS[k], 300, 1.0, False); print(k, t["predicted_per_second"], t["predicted_n"], t.get("draft_n_accepted"))
else:
    ps = json.load(open("copy_prompts.json"))["mvs"]
    for k in list(ps)[:2]:
        t = chat(ps[k], 600, 0.0, True); print(k, t["predicted_per_second"], t["predicted_n"], t.get("draft_n_accepted"))
EOF
nsys stop --session=$sess
sleep 2
pkill -f "/root/bin/$bin/llama-server" ; sleep 5
cd $P && nsys stats -q --report cuda_api_sum,cuda_gpu_kern_sum,cuda_gpu_mem_time_sum --format csv -o $label $label.nsys-rep > /dev/null 2>&1
nsys export -q --type sqlite -o $label.sqlite --force-overwrite=true $label.nsys-rep > /dev/null 2>&1
ls -la $P | grep $label
