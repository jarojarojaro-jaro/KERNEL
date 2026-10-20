#!/usr/bin/env bash
# Report 35 E4 (32a E2): prefill variance across fresh process starts. N fresh llama-bench processes (pp512, 5 reps
# each, topka build, production KV/FA, PM4 env explicit). A bimodal ~-13% cluster = MES queue/pipe placement (gfx12
# in strata). Run ONLY from the GPU queue.
set -euo pipefail
bin=${BIN:-$HOME/llama-topka}/bin
out=${OUT:-$HOME/qwen-opt/xtxlab/logs/e4_fresh.jsonl}
export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0 LD_LIBRARY_PATH="$bin:/opt/rocm/core-10.0/lib"
pkill -f 'llama-topka/bin/llama-server' && sleep 5 || true
"$HOME/qwen-opt/lookup/vram_ok.sh"
for i in $(seq "${N:-10}"); do
    taskset -c 2-5 "$bin/llama-bench" -m "$HOME/models/Qwen3.8-27B-UD-Q4_K_XL.gguf" -ngl 99 -fa 1 -ctk q4_0 -ctv q4_0 \
        -p 512 -n 0 -r 5 -o jsonl | python3 -c "
import json, sys
for l in sys.stdin:
    r = json.loads(l)
    print(json.dumps({'start': $i, 'avg_ts': r['avg_ts'], 'samples_ts': r['samples_ts']}))" | tee -a "$out"
done
