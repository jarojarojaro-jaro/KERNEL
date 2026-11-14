#!/usr/bin/env bash
# K-013 baseline: verify-width cost V(w) on the production engine (topka-q70), XTX, PM4 as production.
# Queue job only. Output: ~/qwen-opt/k013/vw.jsonl
set -uo pipefail
cd ~/qwen-opt/k013
M=$HOME/models/orca/Qwen3.8-27B-Uncensored-Q4_K_M.gguf
export LD_LIBRARY_PATH=/opt/rocm/core-10.0/lib:/opt/rocm/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0 GGML_HIP_FA_D256_VAR=83
grep -q '^1: 2200Mhz' < <(sed -n '/^OD_SCLK:/,/^OD_MCLK:/p' /sys/class/drm/card0/device/pp_od_clk_voltage) \
    && echo "eco: OD_SCLK 2200" || echo "WARNING: OD_SCLK is not 2200"
taskset -c 2-5 nice -n 5 "$HOME/llama-topka/bin/llama-bench" -m "$M" -ngl 999 -fa 1 -ctk q4_0 -ctv q4_0 \
    -p 1,5,8,9,16 -n 0 -d 2048,32768 -r 3 -o jsonl > vw.jsonl 2> vw.err
rc=$?
python3 - <<'EOF'
import json
rows = [json.loads(l) for l in open("vw.jsonl") if l.strip()]
for d in sorted({r["n_depth"] for r in rows}):
    v = {r["n_prompt"]: 1000 * r["n_prompt"] / r["avg_ts"] for r in rows if r["n_depth"] == d}
    print(f"depth {d}: " + "  ".join(f"V({w})={v[w]:.2f} ms" for w in sorted(v)) + f"  V16-V5={v[16]-v[5]:.2f} ms")
EOF
exit $rc
