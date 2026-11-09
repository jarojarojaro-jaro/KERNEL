#!/usr/bin/env bash
# Step 4: bit-exactness of the variants. One plain server per variant (production model, KV q4_0, ub 512, no spec),
# a 12000-token prompt from the frozen corpus (24 ubatches at growing depth -> the <256,256,32,2> kernel) + a short one,
# T=0, 24 tokens, top-5 logprobs; md5 of the JSON. "prod" = the installed ~/llama-topka binary (= our VAR 0 numerics?).
# -> res/md5.txt: "VAR md5 n_prompt"
set -uo pipefail
. "$HOME/qwen-opt/fa-d256/common.sh"
[ -f "$D/BUILD_OK" ] || { echo "no BUILD_OK"; exit 1; }
port=18762
trap 'pkill -f "llama-server.*--port $port" 2>/dev/null || true' EXIT
trap 'exit 1' TERM INT
ok=$(awk '$2=="PASS"{print $1}' "$D/res/tbo.txt")
list="prod"
for v in $ok; do case " 0 $VARS_LOSSLESS 7 15 " in *" $v "*) list="$list $v" ;; esac; done
echo "md5 list: $list"
: > "$D/res/md5.txt"
for v in $list; do
    b=$BIN; var=$v; [ "$v" = prod ] && { b=$PROD; var=0; }
    GGML_HIP_FA_D256_VAR=$var LD_LIBRARY_PATH=$b:/opt/rocm/core-10.0/lib taskset -c 2-5 "$b/llama-server" --port $port \
        --host 127.0.0.1 -np 1 -m "$M" -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c 16384 -ub 512 > "$D/logs/md5-srv-$v.log" 2>&1 &
    pid=$!
    for _ in $(seq 240); do curl -sf http://127.0.0.1:$port/health >/dev/null && break; sleep 1; done
    python3 - "$port" "$D/corpus.txt" > "$D/res/md5-$v.json" <<'EOF'
import json, sys, urllib.request
port, corpus = sys.argv[1], sys.argv[2]
def post(path, body):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=900).read())
toks = post("/tokenize", {"content": open(corpus, encoding="utf-8").read()[:200000]})["tokens"][:12000]
def run(p):
    r = post("/completion", {"prompt": p, "n_predict": 24, "temperature": 0, "n_probs": 5, "cache_prompt": False})
    return {"content": r["content"], "probs": r.get("completion_probabilities"), "n_prompt": r["timings"]["prompt_n"]}
print(json.dumps([run(toks), run("The capital of France is")]))
EOF
    kill -TERM $pid; for _ in $(seq 60); do kill -0 $pid 2>/dev/null || break; sleep 1; done; kill -9 $pid 2>/dev/null; wait $pid 2>/dev/null
    seen=$(grep -c "GGML_HIP_FA_D256_VAR=$var\b" "$D/logs/md5-srv-$v.log")
    echo "$v $(md5sum < "$D/res/md5-$v.json" | cut -c1-8) n_prompt=$(python3 -c "import json;print([x['n_prompt'] for x in json.load(open('$D/res/md5-$v.json'))])" 2>/dev/null) var_log=$seen" | tee -a "$D/res/md5.txt"
done
