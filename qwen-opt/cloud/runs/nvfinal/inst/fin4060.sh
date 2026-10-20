#!/usr/bin/env bash
# ON the shared build server (Vast 56811633, RTX 4060 Ti 16 GB) while it keeps serving rbuild: the nv-final harness
# (fin.sh / fin3060.sh) on the 16 GB files the 5060 Ti used. Benchmarks run on CPUs 0-7 (taskset), a background loop
# re-pins every build process to CPUs 8-31; uptime is logged per arm so build noise stays visible.
# Arms: U0 upstream `-m` only | U1 upstream + 5060 Ti flags (-fit off -ngl 99 -t 8, KV q8_0, 32k, Qwen: MTP n=4) |
# T cuda-topka2 + U1 flags (+ Qwen: 64k draft vocab, iq4_xs heads, lookup W16, cache share, LLAMA_GPU_VERIFY).
# Order per model: [Qwen: gate md5 GPU_VERIFY 0 vs 1] llama-bench U T T U, servers U0 U1 T | T U1 U0.
set -uo pipefail
H=/root/cloud4060; M=/root/models4060; B=/root/src4060   # direct sm_89 builds (b89), GGML_CCACHE=OFF
RES=/root/results4060; L=$RES/logs; G=$RES/gate
mkdir -p "$L" "$G"
UP=$B/upstream/b89/bin; TK=$B/cuda-topka2/b89/bin
CUDA_LIB=/home/jaro/opt/cuda-12.8/lib64
PORT=18761
BC="taskset -c 0-7"
vram() { nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1; }
say() { echo "=== $(date +%T) $*"; }
load() { echo "{\"t\":\"$(date +%T)\",\"what\":\"$1\",\"loadavg\":\"$(cut -d' ' -f1-3 /proc/loadavg)\",\"builds\":$(pgrep -fc 'remote-build.sh' || true)}" >> "$L/load.jsonl"; }

# keep-alive + build pinning (children inherit the affinity of their pinned parents)
( while sleep 5; do
    touch /root/bf/last-activity
    for p in $(pgrep -f 'remote-build.sh|cmake|ninja|gmake|make |cc1|nvcc|cicc|ptxas|clang|/ld'); do
        taskset -a -cp 8-31 "$p" > /dev/null 2>&1
    done
  done ) &
keeper=$!

pid=
srv_stop() {
    [ -n "$pid" ] || return 0
    kill "$pid" 2>/dev/null
    for _ in $(seq 30); do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
    kill -9 "$pid" 2>/dev/null; wait "$pid" 2>/dev/null; pid=
    sleep 3
}
trap 'srv_stop; kill $keeper' EXIT

TV=1
srv() {  # model arm log
    local model=$1 arm=$2 log=$3 gguf common extra=()
    case $model in
        qwen) gguf=$M/Qwen3.8-27B-UD-Q3_K_XL.gguf
              extra=(--spec-type draft-mtp --spec-draft-n-max 4 -ctkd q8_0 -ctvd q8_0) ;;
        lfm)  gguf=$M/LFM2.5-24B-A2B-QAD-Q4_0.gguf; extra=(-b 2048 -ub 2048) ;;
    esac
    common=(-m "$gguf" -fit off -ngl 99 -t 8 -fa on -ctk q8_0 -ctv q8_0 -c 32768 -np 1 --jinja --cache-ram 8192
            --reasoning-effort low --host 127.0.0.1 --port $PORT --no-webui "${extra[@]}")
    case $arm in
        U0) LD_LIBRARY_PATH=$UP:$CUDA_LIB $BC $UP/llama-server -m "$gguf" --host 127.0.0.1 --port $PORT --no-webui > "$log" 2>&1 & ;;
        U1) LD_LIBRARY_PATH=$UP:$CUDA_LIB $BC $UP/llama-server "${common[@]}" > "$log" 2>&1 & ;;
        T)  if [ "$model" = qwen ]; then
                env LD_LIBRARY_PATH=$TK:$CUDA_LIB LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_SERVER_CACHE_SHARE_MIN=1024 \
                    LLAMA_GPU_VERIFY=$TV LLAMA_SERVER_REASONING_CONTROL=0 $BC $TK/llama-server "${common[@]}" \
                    --spec-draft-vocab $H/draft_vocab_qwen38.txt --spec-draft-vocab-n 65536 \
                    --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs > "$log" 2>&1 &
            else
                env LD_LIBRARY_PATH=$TK:$CUDA_LIB LLAMA_SERVER_CACHE_SHARE_MIN=1024 LLAMA_GPU_VERIFY=$TV \
                    LLAMA_SERVER_REASONING_CONTROL=0 $BC $TK/llama-server "${common[@]}" > "$log" 2>&1 &
            fi ;;
    esac
    pid=$!
    for _ in $(seq 600); do
        curl -sf "http://127.0.0.1:$PORT/health" > /dev/null && return 0
        kill -0 "$pid" 2>/dev/null || { wait "$pid" 2>/dev/null; pid=; return 1; }
        sleep 1
    done
    srv_stop; return 1
}

arm() {  # model arm pass full(1=also mvs + long 16k)
    local model=$1 a=$2 p=$3 full=$4 label=$1.$2.p$3; local slog=$L/$label.server.log
    say "arm $label"; load "$label start"
    local v0; v0=$(vram)
    srv "$model" "$a" "$slog" || { say "$label failed"; tail -20 "$slog"; return 0; }
    sleep 3
    local v1 nctx; v1=$(vram)
    nctx=$(curl -sf "http://127.0.0.1:$PORT/props" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("default_generation_settings",{}).get("n_ctx") or d.get("n_ctx"))' 2>/dev/null || echo "?")
    echo "{\"label\":\"$label\",\"vram_before_mb\":$v0,\"vram_loaded_mb\":$v1,\"n_ctx\":\"$nctx\",\"gpu_verify\":\"$([ "$a" = T ] && echo $TV || echo -)\"}" | tee -a "$L/vram.jsonl"
    (cd "$L" && $BC python3 $H/spec_sweep.py --label "$label" --port $PORT --temps 1.0 --seeds 1,2,3 --tokens 400)
    if [ "$full" = 1 ]; then
        $BC python3 $H/copy_bench.py --label "$label" --port $PORT --set mvs --temps 0.0 --tokens 1024 --out "$L/copy_bench.jsonl"
        $BC python3 $H/long_bench.py --label "$label" --port $PORT --sizes 512,16k --out "$L/long.jsonl"
    fi
    echo "{\"label\":\"$label\",\"vram_peak_end_mb\":$(vram)}" >> "$L/vram.jsonl"
    load "$label end"
    srv_stop
    grep -h -E "draft acceptance rate" "$slog" 2>/dev/null | tail -1 || true
}

lb() {  # model gguf depth(0|1)
    local model=$1 gguf=$2 i=0
    local base=(-m "$gguf" -ngl 99 -fa 1 -ctk q8_0 -ctv q8_0 -t 8 -o jsonl)
    local kinds=(std); [ "$3" = 1 ] && kinds+=(depth)
    for kind in "${kinds[@]}"; do
        local tests=(-p 512,4096 -n 128 -r 3); i=0
        [ $kind = depth ] && tests=(-p 0 -n 128 -d 16384 -r 2)
        for a in U T T U; do
            i=$((i + 1)); local out=$L/lb.$model.$a.r$i.jsonl
            [ $kind = depth ] && out=$L/lbd.$model.$a.r$i.jsonl
            load "lb $kind $model $a r$i start"
            case $a in
                U) LD_LIBRARY_PATH=$UP:$CUDA_LIB $BC $UP/llama-bench "${base[@]}" "${tests[@]}" > "$out" 2> "$out.err" ;;
                T) env LD_LIBRARY_PATH=$TK:$CUDA_LIB LLAMA_GPU_VERIFY=$TV $BC $TK/llama-bench "${base[@]}" "${tests[@]}" > "$out" 2> "$out.err" ;;
            esac
            load "lb $kind $model $a r$i end"
            say "lb $kind $model $a r$i: $(jq -r '"\(.n_prompt)/\(.n_gen)@\(.n_depth // 0) \((.avg_ts * 10 | round) / 10)"' "$out" | tr '\n' ' ')"
        done
    done
}

{ nvidia-smi -q; } > "$RES/nvidia-smi-q.txt"
{ uname -a; lscpu; free -g; df -h /root; nproc; cat /root/qwenbench-label; } > "$RES/system.txt" 2>&1
for d in "$UP" "$TK"; do LD_LIBRARY_PATH=$d:$CUDA_LIB $d/llama-server --version > "$RES/version-$(basename "$(dirname "$(dirname "$d")")").txt" 2>&1; done

# ---- gate (Qwen, T server): test-backend-ops + md5 LLAMA_GPU_VERIFY=0 vs 1 ----
say "gate: test-backend-ops"; tbo_ok=1
for op in TOP_K GET_ROWS SUM_ROWS; do
    LD_LIBRARY_PATH=$TK:$CUDA_LIB $BC $TK/test-backend-ops test -b CUDA0 -o $op > "$G/tbo-$op.log" 2>&1; rc=$?
    say "tbo $op rc=$rc $(grep -E 'tests passed' "$G/tbo-$op.log" | tail -1)"
    [ $rc = 0 ] || tbo_ok=0
done
for v in 0 1; do
    TV=$v; say "gate: md5 LLAMA_GPU_VERIFY=$v"; load "gate v$v"
    srv qwen T "$G/gate.v$v.server.log" || { say "gate server v$v failed"; tail -20 "$G/gate.v$v.server.log"; continue; }
    (cd $H && $BC python3 gate_chat.py --label gate.v$v --port $PORT --out "$G/gate_chat.jsonl")
    $BC python3 $H/copy_bench.py --label gate.v$v --port $PORT --set mvs --temps 0.0 --tokens 1024 --out "$G/copy_bench.jsonl"
    $BC python3 $H/copy_bench.py --label gate.v$v --port $PORT --set short --temps 0.0 --tokens 512 --out "$G/copy_bench.jsonl"
    srv_stop
done
md5s() {
    { jq -r --arg l gate.v$1 'select(.label == $l) | "\(.prompt) \(.temp) \(.md5)"' "$G/gate_chat.jsonl"
      jq -r --arg l gate.v$1 'select(.label == $l) | .set as $s | .prompts | to_entries[] | "\($s) \(.key) \(.value.md5 | join(","))"' "$G/copy_bench.jsonl"; } 2>/dev/null
}
md5s 0 > "$G/md5.v0.txt"; md5s 1 > "$G/md5.v1.txt"
n0=$(wc -l < "$G/md5.v0.txt")
if [ "$n0" -ge 22 ] && cmp -s "$G/md5.v0.txt" "$G/md5.v1.txt"; then md5_ok=1; else md5_ok=0; fi
diff "$G/md5.v0.txt" "$G/md5.v1.txt" > "$G/md5.diff"
if [ $tbo_ok = 1 ] && [ $md5_ok = 1 ]; then TV=1; else TV=0; fi
echo "{\"tbo_ok\":$tbo_ok,\"md5_ok\":$md5_ok,\"md5_rows\":$n0,\"T_gpu_verify\":$TV}" | tee "$G/gate.json"

# ---- Qwen ----
lb qwen $M/Qwen3.8-27B-UD-Q3_K_XL.gguf 1
arm qwen U0 1 1; arm qwen U1 1 1; arm qwen T 1 1
arm qwen T 2 0;  arm qwen U1 2 0; arm qwen U0 2 0
# ---- LFM ----
lb lfm $M/LFM2.5-24B-A2B-QAD-Q4_0.gguf 0
arm lfm U0 1 0; arm lfm U1 1 0; arm lfm T 1 0
arm lfm T 2 0;  arm lfm U1 2 0; arm lfm U0 2 0
touch "$RES/main.done"; say "fin4060 done"
