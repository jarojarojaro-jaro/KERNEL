#!/usr/bin/env bash
# Kernel-level GB/s of the quantized mat-vec in the full-step microbench (test-mmvq-bw -g step: every Bonsai 2.5 27B
# matrix of a decode step, ~7.2 GB) under rocprofv3, one process per variant. Runs ON the box.
# usage: bw-prof.sh BUILD_BIN NCOLS VARIANT...   VARIANT: base | NAME=VAL,NAME=VAL
set -uo pipefail
B=$1 N=$2; shift 2
export GGML_HIP_PM4=0 LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib
I=20; out=$HOME/qwen-opt/bonsai25/out/bwprof-$(date +%H%M%S); mkdir -p "$out"
for v in "$@"; do
  d=$out/n$N-$(echo "$v" | tr -c 'A-Za-z0-9=_\n' '_' | cut -c1-100); mkdir -p "$d"
  ( cd "$d" && taskset -c 2-5 timeout 300 /opt/rocm/core-10.0/bin/rocprofv3 --kernel-trace --stats --output-format csv -d "$d" -o p -- \
      "$B/test-mmvq-bw" -n "$N" -g step -r 1 -i $I "$v" > bench.txt 2>&1 )
  f=$(find "$d" -name "*kernel_stats.csv" | head -1)
  [ -n "$f" ] || { echo "PROF n=$N $v: no kernel stats"; tail -3 "$d/bench.txt"; continue; }
  python3 - "$v" "$f" "$d/bench.txt" $((I + 2)) "$N" <<'PY'
import csv, re, sys
v, f, b, runs, n = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
mb = float(re.search(r"step ([0-9.]+)", open(b).read()).group(1))   # weight MB per step
rows = list(csv.DictReader(open(f)))
mv  = sum(float(r["TotalDurationNs"]) for r in rows if "mul_mat_vec_q" in r["Name"])
tot = sum(float(r["TotalDurationNs"]) for r in rows)
print(f"PROF n={n} {v}: mat-vec {mv/runs/1e6:.3f} ms/step = {mb*1e6*runs/mv:.1f} GB/s (kernel time), "
      f"all kernels {tot/runs/1e6:.3f} ms/step = {mb*1e6*runs/tot:.1f} GB/s")
for r in sorted(rows, key=lambda r: -float(r["TotalDurationNs"]))[:5]:
    print(f"   {float(r['TotalDurationNs'])/tot*100:5.1f}% {int(r['Calls'])//runs:5d}/step {float(r['AverageNs'])/1e3:7.1f}us  {r['Name'][:110]}")
PY
done
