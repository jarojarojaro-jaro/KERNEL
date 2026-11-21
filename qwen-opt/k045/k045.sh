#!/usr/bin/env bash
# K-045 (G1): verify-cost curve of LFM2.5-24B-A2B Q5_K_M: llama-bench pN = one N-token ubatch at depth 0 and 32768,
# T(N) = N / (t/s) in ms vs the model of metody/model-kosztu-weryfikacji-moe (gates T(8) <= 13.6 ms, T(3) <= 6.8 ms).
# Production LFM build ~/llama-topka, KV q8_0, -b/-ub 2048 (depth fill), PM4 off. K-033 DPM poll alongside. Queue only.
set -u
here=$(cd "$(dirname "$0")" && pwd); out=$here/out; mkdir -p "$out"
~/qwen-opt/l1tok/chat8080.sh stop
bash ~/qwen-opt/k033/dpm_poll.sh "$out/dpm-k045.txt" & poll=$!
trap 'kill $poll 2>/dev/null' EXIT
GGML_HIP_PM4=0 LD_LIBRARY_PATH=$HOME/llama-topka/bin:/opt/rocm/core-10.0/lib timeout 540 ~/llama-topka/bin/llama-bench \
    -m ~/models/lfm/LFM2.5-24B-A2B-Q5_K_M.gguf -ngl 999 -fa 1 -ctk q8_0 -ctv q8_0 -b 2048 -ub 2048 \
    -p 1,2,3,4,5,8,16 -n 0 -d 0,32768 -r 3 -o jsonl > "$out/k045.jsonl" 2> "$out/k045.err"
echo "rc $?"
python3 - "$out/k045.jsonl" <<'PY'
import json, sys
model = {1: 3.42, 2: 4.48, 3: 5.47, 4: 6.41, 5: 7.28, 8: 9.58, 16: 13.93}
for r in (json.loads(l) for l in open(sys.argv[1]) if l.startswith("{")):
    n = r["n_prompt"]
    print(f"d {r['n_depth']:>6} p{n:<3} {r['avg_ts']:8.1f} t/s  T(N) {1000 * n / r['avg_ts']:6.2f} ms  model {model[n]:5.2f} ms")
PY
kill $poll
nice python3 ~/qwen-opt/k033/dpm_sum.py "$out/dpm-k045.txt"
