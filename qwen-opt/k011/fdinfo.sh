#!/usr/bin/env bash
# K-011: VRAM->GTT eviction check: drm fdinfo of the production-config server (ctx 262144, port 18794) before the prompt,
# after a ~131k-token prefill and after 256 decoded tokens. Queue only.
set -u
export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0
P=18794; here=$(cd "$(dirname "$0")" && pwd); out=$here/out; mkdir -p "$out"
PORT=$P LOG=$out/server.log setsid ~/qwen-opt/run-topka.sh uncensored > "$out/launch.log" 2>&1 &
srv=$!
trap 'kill -TERM -- -$srv 2>/dev/null; for _ in $(seq 30); do kill -0 $srv 2>/dev/null || break; sleep 1; done; kill -KILL -- -$srv 2>/dev/null' EXIT
for _ in $(seq 240); do curl -sf 127.0.0.1:$P/health > /dev/null && break; sleep 1; done
pid=$(pgrep -f "llama-server.*--port $P" | head -1)
snap() {
    echo "== $1 (pid $pid)"
    for f in /proc/$pid/fdinfo/*; do grep -q '^drm-client-id' "$f" 2>/dev/null && { echo "-- $f"; grep -E '^(drm-client-id|drm-memory|drm-resident|drm-total|drm-shared|amd-)' "$f"; }; done | awk '!seen[$0]++ || /^--/'
}
snap before
python3 - "$P" "$out" <<'PY'
import json, sys, time, urllib.request
port, out = sys.argv[1], sys.argv[2]
def post(path, body):
    r = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=900))
text = open("/home/jaro/qwen-opt/xtxbench/corpus.txt", encoding="utf-8", errors="ignore").read()
toks = post("/tokenize", {"content": text[:700000]})["tokens"][:131000]
prompt = post("/detokenize", {"tokens": toks})["content"]
open(out + "/prompt.txt", "w").write(prompt)
t = time.time(); r = post("/completion", {"prompt": prompt, "n_predict": 1, "temperature": 0, "cache_prompt": True})
print("prefill", r["timings"]["prompt_n"], "tok", round(r["timings"]["prompt_per_second"], 1), "t/s", round(time.time() - t, 1), "s", flush=True)
PY
snap after-prefill
python3 - "$P" "$out" <<'PY'
import json, sys, urllib.request
port, out = sys.argv[1], sys.argv[2]
prompt = open(out + "/prompt.txt").read()
r = urllib.request.Request(f"http://127.0.0.1:{port}/completion", data=json.dumps({"prompt": prompt, "n_predict": 256, "temperature": 0, "ignore_eos": True, "cache_prompt": True}).encode(), headers={"Content-Type": "application/json"})
t = json.load(urllib.request.urlopen(r, timeout=900))["timings"]
print("decode", t["predicted_n"], "tok", round(t["predicted_per_second"], 2), "t/s, prompt_n", t["prompt_n"], flush=True)
PY
snap after-256
