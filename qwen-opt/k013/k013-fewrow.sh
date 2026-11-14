#!/usr/bin/env bash
# K-013: V(w) on upstream 6ad15f48 (few-row MMQ #31533 + RDNA3 WMMA port), same model/flags as the production baseline vw.jsonl.
set -uo pipefail
cd ~/qwen-opt/k013
M=$HOME/models/orca/Qwen3.8-27B-Uncensored-Q4_K_M.gguf
export LD_LIBRARY_PATH=/opt/rocm/core-10.0/lib:/opt/rocm/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
export GGML_HIP_PM4=0
grep -q "^1: 2200Mhz" < <(sed -n "/^OD_SCLK:/,/^OD_MCLK:/p" /sys/class/drm/card0/device/pp_od_clk_voltage) && echo "eco: OD_SCLK 2200"
taskset -c 2-5 nice -n 5 "$HOME/wt/fewrow-hip/build-hip/bin/llama-bench" -m "$M" -ngl 999 -fa 1 -ctk q4_0 -ctv q4_0 \
    -p 1,5,8,9,16 -n 0 -d 2048,32768 -r 3 -o jsonl > vw-fewrow.jsonl 2> vw-fewrow.err
