#!/usr/bin/env bash
# decode kernel profile (rocprofv3 kernel stats) + llama-bench tg64 for Bonsai 2.5 Uncensored Q2_0 / PTQ1_0 on the prism build
set -uo pipefail
B=${B:-$HOME/wt/topka-best/build-hip/bin}; export GGML_HIP_PM4=0 LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib
D=$HOME/models/bonsai25; out=$HOME/qwen-opt/bonsai25/out/prof-$(date +%H%M%S); mkdir -p $out
~/qwen-opt/l1tok/chat8080.sh stop
for m in Q2_0; do
  taskset -c 2-5 timeout 200 $B/llama-bench -m $D/Ternary-Bonsai-2.5-27B-Uncensored-$m-mtp.gguf -ngl 999 -fa 1 -ctk q4_0 -ctv q4_0 -p 512 -n 128 -r 3 2>&1 | grep -E "pp512|tg128"
done
cd $out && taskset -c 2-5 timeout 300 /opt/rocm/core-10.0/bin/rocprofv3 --kernel-trace --stats --output-format csv -d $out -o prof -- \
  $B/llama-bench -m $D/Ternary-Bonsai-2.5-27B-Uncensored-Q2_0-mtp.gguf -ngl 999 -fa 1 -ctk q4_0 -ctv q4_0 -p 0 -n 64 -r 1 > bench.txt 2>&1
f=$(find $out -name "*kernel_stats.csv" | head -1); echo "stats: $f"
python3 - "$f" <<'PY'
import csv,sys
rows=list(csv.DictReader(open(sys.argv[1]))); tot=sum(float(r['TotalDurationNs']) for r in rows)
for r in sorted(rows,key=lambda r:-float(r['TotalDurationNs']))[:18]:
    print(f"{float(r['TotalDurationNs'])/tot*100:5.1f}% {int(r['Calls']):6d} {float(r['AverageNs'])/1e3:8.1f}us  {r['Name'][:150]}")
print('total ms', tot/1e6)
PY
journalctl -k --since "-10min" --no-pager | grep -c gfxhub
