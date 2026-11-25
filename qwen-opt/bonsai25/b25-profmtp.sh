#!/usr/bin/env bash
# kernel profile of a speculative step: prism Q2_0 + MTP n2, ctx 262144, one T=0.7 request of 200 tokens under rocprofv3
set -uo pipefail
B=${B:-$HOME/wt/prism/build-hip/bin}; export GGML_HIP_PM4=0 LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib
M=$HOME/models/bonsai25/Ternary-Bonsai-2.5-27B-Uncensored-Q2_0-mtp.gguf; out=$HOME/qwen-opt/bonsai25/out/profmtp-$(date +%H%M%S); mkdir -p $out; PORT=18796
~/qwen-opt/l1tok/chat8080.sh stop
cd $out; taskset -c 2-5 /opt/rocm/core-10.0/bin/rocprofv3 --kernel-trace --stats --output-format csv -d $out -o prof -- \
  $B/llama-server -m $M -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c 262144 -np 1 --jinja --no-webui --port $PORT \
  --spec-type draft-mtp --spec-draft-n-max ${N:-2} -ctkd q4_0 -ctvd q4_0 > srv.log 2>&1 & srv=$!
for _ in $(seq 300); do curl -sf 127.0.0.1:$PORT/health >/dev/null && break; sleep 1; done
for t in 0.7 0.7; do curl -s 127.0.0.1:$PORT/v1/chat/completions -d "{\"messages\":[{\"role\":\"user\",\"content\":\"Write a detailed essay about the history of the printing press.\"}],\"temperature\":$t,\"max_tokens\":200,\"chat_template_kwargs\":{\"enable_thinking\":false}}" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['timings'])"; done
kill -INT $srv; wait $srv
f=$(find $out -name "*kernel_stats.csv" | head -1)
python3 - "$f" <<'PY'
import csv,sys
rows=list(csv.DictReader(open(sys.argv[1]))); tot=sum(float(r['TotalDurationNs']) for r in rows)
for r in sorted(rows,key=lambda r:-float(r['TotalDurationNs']))[:22]:
    print(f"{float(r['TotalDurationNs'])/tot*100:5.1f}% {int(r['Calls']):7d} {float(r['AverageNs'])/1e3:8.1f}us  {r['Name'][:140]}")
print('total ms', tot/1e6)
PY
grep -E "draft acceptance|eval time" srv.log | tail -4
journalctl -k --since "-10min" --no-pager | grep -c gfxhub
