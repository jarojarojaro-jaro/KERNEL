#!/usr/bin/env bash
# greedy parity: md5 of 3 x 256-token T=0 answers (MTP n2 off and on) for engine dirs given; prints md5 per engine/mode
set -uo pipefail
M=$HOME/models/bonsai25/Ternary-Bonsai-2.5-27B-Uncensored-Q2_0-mtp.gguf; PORT=18796
export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0
~/qwen-opt/l1tok/chat8080.sh stop
for spec in "$@"; do B=${spec%%@*}; E=""; [[ $spec == *@* ]] && E=${spec#*@}; for mode in ${MODES:-none mtp}; do
  sp=(); [ $mode = mtp ] && sp=(--spec-type draft-mtp --spec-draft-n-max 2 -ctkd q4_0 -ctvd q4_0)
  env ${E//,/ } LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib taskset -c 2-5 $B/llama-server -m $M -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c 32768 -np 1 --jinja --port $PORT "${sp[@]}" > /tmp/par.log 2>&1 & srv=$!
  for _ in $(seq 300); do curl -sf 127.0.0.1:$PORT/health >/dev/null && break; sleep 1; done
  h=$(for p in "Explain TCP congestion control." "Write a Python quicksort with tests." "Opowiedz o historii Krakowa."; do
    curl -s 127.0.0.1:$PORT/v1/chat/completions -d "{\"messages\":[{\"role\":\"user\",\"content\":\"$p\"}],\"temperature\":0,\"max_tokens\":256,\"chat_template_kwargs\":{\"enable_thinking\":false}}" | python3 -c "import json,sys;print(json.load(sys.stdin)['choices'][0]['message']['content'])"; done | md5sum | cut -c1-8)
  echo "PARITY $(basename $(dirname $(dirname $B))) ${E:-default} $mode $h"
  kill -TERM $srv; wait $srv 2>/dev/null
done; done
journalctl -k --since "-15min" --no-pager | grep -c gfxhub
