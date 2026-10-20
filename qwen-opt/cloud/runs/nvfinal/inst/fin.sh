#!/usr/bin/env bash
# ON the instance: fin.sh qwen|uncensored — one model per 3090 (two instances run in parallel). The XTX final
# before/after test set (~/qwen-opt/bench-final) plus context-depth metrics. Arms: U0 upstream `-m` only | U1 upstream
# + production flags + MTP n=4 | T cuda-topka2 (lookup W16 + cache share + LLAMA_GPU_VERIFY).
# Order: gate, llama-bench U T T U (pp512/pp4096/tg128 r3, then tg128 at depth 16k/32k/64k r2), servers U0 U1 T (p1),
# T U1 U0 (p2). Per server: spec_sweep T=1 (6 prompts x seeds 1-3) and T=0 (seed 1), mvs T=0, copy T=0,
# long_bench.py (512/2k/16k/32k/60k prompts, T=0 and T=1: prefill t/s, TTFT, decode with speculation on filled KV).
# 0) gate: test-backend-ops TOP_K/GET_ROWS/SUM_ROWS/MUL_MAT (CUDA0 vs CPU) + md5 LLAMA_GPU_VERIFY=0 vs 1 (this model,
#    chat T=0 and T=1 s1, mvs and copy T=0). Gate failed -> T runs with LLAMA_GPU_VERIFY=0.
# Logs: $RES/logs (bench-final/logs names), gate in $RES/gate.
set -uo pipefail
H=/root/cloud; M=/root/models
RES=$(readlink -f /root/results/current); L=$RES/logs; G=$RES/gate
UP=/root/bin/upstream; TK=/root/bin/topka2
PORT=18701
MODEL=$1
case $MODEL in qwen) GGUF_FILE=Qwen3.8-27B-UD-Q4_K_XL.gguf ;; uncensored) GGUF_FILE=Qwen3.8-27B-Uncensored-Q4_K_M.gguf ;; *) exit 2 ;; esac
deadline=$(cat /root/qwenbench-deadline 2>/dev/null || echo $(( $(date +%s) + 86400 )))
time_left() { [ "$(date +%s)" -lt $(( deadline - ${1:-900} )) ]; }
vram() { nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1; }
say() { echo "=== $(date +%T) $*"; }

pid=
srv_stop() {
    [ -n "$pid" ] || return 0
    kill "$pid" 2>/dev/null
    for _ in $(seq 30); do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
    kill -9 "$pid" 2>/dev/null; wait "$pid" 2>/dev/null; pid=
    sleep 3
}
trap srv_stop EXIT

TV=1   # LLAMA_GPU_VERIFY for T, set to 0 by a failed gate
# srv model arm ctx log : start one server, 0 = healthy
srv() {
    local model=$1 arm=$2 ctx=$3 log=$4 gguf
    case $model in
        qwen) gguf=$M/Qwen3.8-27B-UD-Q4_K_XL.gguf ;;
        uncensored) gguf=$M/Qwen3.8-27B-Uncensored-Q4_K_M.gguf ;;
    esac
    local prod=(-m "$gguf" -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c "$ctx" -np 1 --jinja --cache-ram 16384
                --reasoning-effort low --host 127.0.0.1 --port $PORT --no-webui
                --spec-type draft-mtp --spec-draft-n-max 4 -ctkd q4_0 -ctvd q4_0)
    case $arm in
        U0) $UP/llama-server -m "$gguf" --host 127.0.0.1 --port $PORT --no-webui > "$log" 2>&1 & ;;
        U1) $UP/llama-server "${prod[@]}" > "$log" 2>&1 & ;;
        T)  env LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_SERVER_CACHE_SHARE_MIN=1024 LLAMA_GPU_VERIFY=$TV \
                LLAMA_SERVER_REASONING_CONTROL=0 $TK/llama-server "${prod[@]}" \
                --spec-draft-vocab $H/draft_vocab_qwen38.txt --spec-draft-vocab-n 65536 \
                --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs > "$log" 2>&1 & ;;
    esac
    pid=$!
    for _ in $(seq 600); do
        curl -sf "http://127.0.0.1:$PORT/health" > /dev/null && return 0
        kill -0 "$pid" 2>/dev/null || { wait "$pid" 2>/dev/null; pid=; return 1; }
        sleep 1
    done
    srv_stop; return 1
}
# srv_ctx model arm log : production ctx 204800, step down like fb_arm.sh U1; sets used_ctx
srv_ctx() {
    for c in 204800 131072 65536; do
        used_ctx=$c
        srv "$1" "$2" "$c" "$3" && return 0
        echo "$1 $2: did not start at ctx $c"; tail -3 "$3"
    done
    return 1
}

arm() {  # model arm pass
    local model=$1 a=$2 p=$3 label=$1.$2.p$3; local slog=$L/$label.server.log
    time_left 600 || { say "deadline: skip $label"; return 0; }
    say "arm $label"
    local v0; v0=$(vram); used_ctx=default
    if [ "$a" = U0 ]; then srv "$model" U0 0 "$slog" || { say "$label failed"; tail -20 "$slog"; return 0; }
    else srv_ctx "$model" "$a" "$slog" || { say "$label failed"; return 0; }; fi
    sleep 3
    local v1 nctx; v1=$(vram)
    nctx=$(curl -sf "http://127.0.0.1:$PORT/props" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("default_generation_settings",{}).get("n_ctx") or d.get("n_ctx"))' 2>/dev/null || echo "?")
    echo "{\"label\":\"$label\",\"vram_before_mb\":$v0,\"vram_loaded_mb\":$v1,\"n_ctx\":\"$nctx\",\"ctx_requested\":\"$used_ctx\",\"gpu_verify\":\"$([ "$a" = T ] && echo $TV || echo -)\"}" | tee -a "$L/vram.jsonl"
    (cd "$L" && python3 $H/spec_sweep.py --label "$label" --port $PORT --temps 1.0 --seeds 1,2,3 --tokens 400)
    (cd "$L" && python3 $H/spec_sweep.py --label "$label" --port $PORT --temps 0.0 --seeds 1 --tokens 400)
    python3 $H/copy_bench.py --label "$label" --port $PORT --set mvs --temps 0.0 --tokens 1024 --out "$L/copy_bench.jsonl"
    python3 $H/copy_bench.py --label "$label" --port $PORT --set short --temps 0.0 --tokens 512 --out "$L/copy_bench.jsonl"
    python3 $H/long_bench.py --label "$label" --port $PORT --out "$L/long.jsonl"
    srv_stop
    grep -h -E "context lookup|draft acceptance rate" "$slog" 2>/dev/null | tail -2 || true
}

lb() {  # model : llama-bench U T T U (fb_lb.sh), then tg128 at depth U T T U
    local model=$1 gguf=$M/$GGUF_FILE i=0
    local base=(-m "$gguf" -ngl 999 -fa 1 -ctk q4_0 -ctv q4_0 -o jsonl)
    for kind in std depth; do
        local tests=(-p 512,4096 -n 128 -r 3); i=0
        [ $kind = depth ] && tests=(-p 0 -n 128 -d 16384,32768,65536 -r 2)
        for a in U T T U; do
            i=$((i + 1)); local out=$L/lb.$model.$a.r$i.jsonl
            [ $kind = depth ] && out=$L/lbd.$model.$a.r$i.jsonl
            time_left 600 || { say "deadline: skip $out"; continue; }
            case $a in
                U) $UP/llama-bench "${base[@]}" "${tests[@]}" > "$out" 2> "$out.err" ;;
                T) env LLAMA_GPU_VERIFY=$TV $TK/llama-bench "${base[@]}" "${tests[@]}" > "$out" 2> "$out.err" ;;
            esac
            say "lb $kind $model $a r$i: $(jq -r '"\(.n_prompt)/\(.n_gen)@\(.n_depth // 0) \((.avg_ts * 10 | round) / 10)"' "$out" | tr '\n' ' ')"
        done
    done
}

wait_model() { for _ in $(seq 1200); do [ -f "$M/$1.ok" ] && return 0; sleep 3; done; say "timeout waiting for $1"; return 1; }

# ---- 0) gate ----
say "gate: test-backend-ops"
tbo_ok=1
for op in TOP_K GET_ROWS SUM_ROWS MUL_MAT; do
    $TK/test-backend-ops test -b CUDA0 -o $op > "$G/tbo-$op.log" 2>&1
    rc=$?
    r=$(grep -E "tests passed" "$G/tbo-$op.log" | tail -1)
    ok=$(grep -cE "^\s*Backend CUDA0: .*OK|Backend CUDA0: OK" "$G/tbo-$op.log")
    say "tbo $op rc=$rc $r ok=$ok"
    { [ $rc = 0 ] && [ "$ok" -gt 0 ]; } || tbo_ok=0
done
wait_model $GGUF_FILE || exit 1
for v in 0 1; do
    TV=$v
    say "gate: md5 LLAMA_GPU_VERIFY=$v"
    srv_ctx $MODEL T "$G/gate.v$v.server.log" || { say "gate server v$v failed"; continue; }
    (cd $H && python3 gate_chat.py --label gate.v$v --port $PORT --out "$G/gate_chat.jsonl")
    python3 $H/copy_bench.py --label gate.v$v --port $PORT --set mvs --temps 0.0 --tokens 1024 --out "$G/copy_bench.jsonl"
    python3 $H/copy_bench.py --label gate.v$v --port $PORT --set short --temps 0.0 --tokens 512 --out "$G/copy_bench.jsonl"
    srv_stop
done
md5s() {  # v -> canonical md5 list
    { jq -r --arg l gate.v$1 'select(.label == $l) | "\(.prompt) \(.temp) \(.md5)"' "$G/gate_chat.jsonl"
      jq -r --arg l gate.v$1 'select(.label == $l) | .set as $s | .prompts | to_entries[] | "\($s) \(.key) \(.value.md5 | join(","))"' "$G/copy_bench.jsonl"; } 2>/dev/null
}
md5s 0 > "$G/md5.v0.txt"; md5s 1 > "$G/md5.v1.txt"
n0=$(wc -l < "$G/md5.v0.txt")
if [ "$n0" -ge 22 ] && cmp -s "$G/md5.v0.txt" "$G/md5.v1.txt"; then md5_ok=1; else md5_ok=0; fi
diff "$G/md5.v0.txt" "$G/md5.v1.txt" > "$G/md5.diff"
if [ $tbo_ok = 1 ] && [ $md5_ok = 1 ]; then TV=1; else TV=0; fi
echo "{\"tbo_ok\":$tbo_ok,\"md5_ok\":$md5_ok,\"md5_rows\":$n0,\"T_gpu_verify\":$TV}" | tee "$G/gate.json"
say "gate done: tbo_ok=$tbo_ok md5_ok=$md5_ok -> T uses LLAMA_GPU_VERIFY=$TV"

# ---- 1) measurement ----
lb $MODEL
arm $MODEL U0 1; arm $MODEL U1 1; arm $MODEL T 1
arm $MODEL T 2;  arm $MODEL U1 2; arm $MODEL U0 2
touch "$RES/main.done"; say "fin done"
