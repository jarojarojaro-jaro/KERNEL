#!/usr/bin/env bash
# ON a RTX 3060 12 GB: Underdog Saluki 27B IQ2-mix with the Kujira MTP head (16e S1). Arms: U0 upstream `-m` only |
# T cuda-topka2 + MTP n=2 (64k draft vocab, iq4_xs heads as 16e e2.sh) + lookup W16 + cache share + LLAMA_GPU_VERIFY=1
# (passed the 3090 gate), KV q8_0, ctx 20480, --cache-ram 8192 (= upstream default; 16384 got the server OOM-killed on
# a 15 GB host in run 1). Order: llama-bench U T T U (pp512/pp4096/tg128 r3), servers U0 T T U0.
# Per server: spec_sweep T=1 (6 prompts x seeds 1-3), long_bench.py 512 and 16k (prefill, TTFT, decode T=0/T=1).
set -uo pipefail
H=/root/cloud; M=/root/models
RES=$(readlink -f /root/results/current); L=$RES/logs
UP=/root/bin/upstream; TK=/root/bin/topka2
PORT=18701
GGUF=$M/Underdog-Saluki-27B-1.0-IQ2-mix-MTP.gguf
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
srv() {  # arm log
    case $1 in
        U0) $UP/llama-server -m "$GGUF" --host 127.0.0.1 --port $PORT --no-webui > "$2" 2>&1 & ;;
        T)  env LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_SERVER_CACHE_SHARE_MIN=1024 LLAMA_GPU_VERIFY=1 \
                LLAMA_SERVER_REASONING_CONTROL=0 $TK/llama-server -m "$GGUF" -ngl 999 -fa on -ctk q8_0 -ctv q8_0 \
                -c 20480 -np 1 --jinja --cache-ram 8192 --reasoning-effort low --host 127.0.0.1 --port $PORT --no-webui \
                --spec-type draft-mtp --spec-draft-n-max 2 -ctkd q8_0 -ctvd q8_0 \
                --spec-draft-vocab $H/draft_vocab_qwen38.txt --spec-draft-vocab-n 65536 \
                --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs > "$2" 2>&1 & ;;
    esac
    pid=$!
    for _ in $(seq 600); do
        curl -sf "http://127.0.0.1:$PORT/health" > /dev/null && return 0
        kill -0 "$pid" 2>/dev/null || { wait "$pid" 2>/dev/null; pid=; return 1; }
        sleep 1
    done
    srv_stop; return 1
}
arm() {  # arm pass
    local label=saluki.$1.p$2; local slog=$L/$label.server.log
    say "arm $label"
    local v0; v0=$(vram)
    srv "$1" "$slog" || { say "$label failed"; tail -20 "$slog"; return 0; }
    # host memory of the server (run 1: T was OOM-killed on a 15 GB host): RSS KiB, used / available MiB every 10 s
    ( p=$pid; while kill -0 "$p" 2>/dev/null; do echo "$(date +%T) rss_kb=$(ps -o rss= -p "$p") $(free -m | awk '/Mem:/ {print "used_mb=" $3, "avail_mb=" $7}')"; sleep 10; done ) > "$L/$label.mem.log" 2>&1 &
    sleep 3
    local v1 nctx; v1=$(vram)
    nctx=$(curl -sf "http://127.0.0.1:$PORT/props" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("default_generation_settings",{}).get("n_ctx") or d.get("n_ctx"))' 2>/dev/null || echo "?")
    echo "{\"label\":\"$label\",\"vram_before_mb\":$v0,\"vram_loaded_mb\":$v1,\"n_ctx\":\"$nctx\"}" | tee -a "$L/vram.jsonl"
    (cd "$L" && python3 $H/spec_sweep.py --label "$label" --port $PORT --temps 1.0 --seeds 1,2,3 --tokens 400)
    python3 $H/long_bench.py --label "$label" --port $PORT --out "$L/long.jsonl" --sizes 512,16k
    srv_stop
    grep -h -E "context lookup|draft acceptance rate" "$slog" 2>/dev/null | tail -2 || true
}
for _ in $(seq 1200); do [ -f "$GGUF.ok" ] && break; sleep 3; done
[ -f "$GGUF.ok" ] || { say "model missing"; exit 1; }
i=0
for a in U T T U; do
    i=$((i + 1)); out=$L/lb.saluki.$a.r$i.jsonl
    case $a in
        U) $UP/llama-bench -m "$GGUF" -ngl 999 -fa 1 -ctk q8_0 -ctv q8_0 -p 512,4096 -n 128 -r 3 -o jsonl > "$out" 2> "$out.err" ;;
        T) env LLAMA_GPU_VERIFY=1 $TK/llama-bench -m "$GGUF" -ngl 999 -fa 1 -ctk q8_0 -ctv q8_0 -p 512,4096 -n 128 -r 3 -o jsonl > "$out" 2> "$out.err" ;;
    esac
    say "lb $a r$i: $(jq -r '"\(.n_prompt)/\(.n_gen) \((.avg_ts * 10 | round) / 10)"' "$out" | tr '\n' ' ')"
done
arm U0 1; arm T 1; arm T 2; arm U0 2
touch "$RES/main.done"; say "fin3060 done"
