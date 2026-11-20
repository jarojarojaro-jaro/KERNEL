#!/usr/bin/env bash
# K-032: KV read amplification in kvq: L2->memory read bytes (GL2C_EA_RDREQ_{32,64,96,128}B_sum; gfx1100 has no
# TCC_EA_RDREQ_*) on attention kernels, llama-bench -p 5 at depth 131072, production binary ~/llama-topka, PM4 off.
# The depth fill uses -ub 512 (a 5-token ubatch fill of 131k would take hours); the measured -p 5 step is one 5-token
# ubatch either way. Prints the last 40 profiled dispatches (the pp5 step) with their read bytes. Queue only.
set -u
export GGML_HIP_PM4=0 LD_LIBRARY_PATH=$HOME/llama-topka/lib:/opt/rocm/core-10.0/lib
here=$(cd "$(dirname "$0")" && pwd); out=$here/out; rm -rf "$out"; mkdir -p "$out"
M=$HOME/models/orca/Qwen3.8-27B-Uncensored-Q4_K_M.gguf
timeout 560 /opt/rocm/bin/rocprofv3 --pmc GL2C_EA_RDREQ_32B_sum GL2C_EA_RDREQ_64B_sum GL2C_EA_RDREQ_96B_sum GL2C_EA_RDREQ_128B_sum \
    --kernel-include-regex 'attn|kvq' -d "$out" -o k032 --output-format csv -- \
    "$HOME/llama-topka/bin/llama-bench" -m "$M" -ngl 999 -fa 1 -ctk q4_0 -ctv q4_0 -p 5 -n 0 -ub 512 -d 131072 -r 1 -o md 2>&1 | grep -vE '^W1120|queue-intercept'
python3 - "$out" <<'PY'
import csv, glob, sys, collections
f = glob.glob(sys.argv[1] + "/**/*counter_collection*.csv", recursive=True)
if not f: print("no counter csv"); sys.exit()
w = {"GL2C_EA_RDREQ_32B_sum": 32, "GL2C_EA_RDREQ_64B_sum": 64, "GL2C_EA_RDREQ_96B_sum": 96, "GL2C_EA_RDREQ_128B_sum": 128}
d = collections.OrderedDict()
for r in csv.DictReader(open(f[0])):
    k = int(r["Dispatch_Id"]); e = d.setdefault(k, [r["Kernel_Name"][:70], 0.0])
    e[1] += w.get(r["Counter_Name"], 0) * float(r["Counter_Value"])
print("profiled dispatches", len(d)); print(collections.Counter(v[0] for v in d.values()).most_common(8))
for k in list(d)[-40:]: print(k, d[k][0], round(d[k][1] / 1e6, 2), "MB")
PY
