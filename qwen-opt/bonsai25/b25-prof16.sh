#!/usr/bin/env bash
# kernel stats of 8- vs 16-token batches (llama-bench -p N -n 0 -ub 16, 10 reps) on a topka build; prints top kernels per N
set -uo pipefail
B=${B:-$HOME/wt/topka-bz16/build-hip/bin}; export GGML_HIP_PM4=0 LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib
M=$HOME/models/bonsai25/Ternary-Bonsai-2.5-27B-Uncensored-Q2_0-mtp.gguf
~/qwen-opt/l1tok/chat8080.sh stop
for n in 8 16; do
  out=$HOME/qwen-opt/bonsai25/out/prof$n-$(date +%H%M%S); mkdir -p $out; cd $out
  taskset -c 2-5 timeout 250 /opt/rocm/core-10.0/bin/rocprofv3 --kernel-trace --stats --output-format csv -d $out -o prof -- \
    $B/llama-bench -m $M -ngl 999 -fa 1 -ctk q4_0 -ctv q4_0 -p $n -n 0 -ub 16 -r 10 > bench.txt 2>&1
  grep -E "pp$n" bench.txt | sed -E "s/ +/ /g" | cut -d"|" -f9,10
  f=$(find $out -name "*kernel_stats.csv" | head -1)
  python3 - "$f" $n <<'PY'
import csv,sys
rows=list(csv.DictReader(open(sys.argv[1]))); tot=sum(float(r['TotalDurationNs']) for r in rows)
print(f"== n={sys.argv[2]} total GPU ms {tot/1e6:.1f}")
for r in sorted(rows,key=lambda r:-float(r['TotalDurationNs']))[:12]:
    print(f"{float(r['TotalDurationNs'])/tot*100:5.1f}% {int(r['Calls']):6d} {float(r['AverageNs'])/1e3:8.1f}us  {r['Name'][:120]}")
PY
done
journalctl -k --since "-10min" --no-pager | grep -c gfxhub
