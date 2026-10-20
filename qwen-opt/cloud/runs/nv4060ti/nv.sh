#!/usr/bin/env bash
# ON the 4060 Ti box (report 31): nv-final harness for Qwen3.8-27B UD-IQ4_XS, KV q4_0 (target + draft), context $C.
#   nv.sh srv <arm> <log>                 start a server (arm U0|U1|T|X), wait for /health (sets $pid)
#   nv.sh sweep <arm> <label> [seeds]     fresh server, spec_sweep T=1 (6 prompts x seeds, 400 tok) [+ mvs if MVS=1]
#   nv.sh full <arm> <pass>               fresh server, spec_sweep T=1 seeds 1,2,3 + mvs T=0 + long 512/16k (pass 1)
#   nv.sh lb <label> <arm>...             llama-bench pp512/pp4096/tg128 per arm in the given order
#   nv.sh gate <label>                    md5 gate on arm X: gate_chat (12) + mvs (4) + copy short (6), XENV applied
# Arms: U0 upstream -m only | U1 upstream + flags + MTP n=4 | T cuda-topka2 2a261101b (+ fork flags) |
#       X = binary $XBIN (default /root/bin/X) with T flags + env $XENV (space-separated VAR=val) [+ $XARGS].
# Benchmarks: taskset -c $BC_CPUS (default 0-3), -t 4; never while a build runs (pgrep check).
set -uo pipefail
R=/root; M=$R/models/${GGUF:-Qwen3.8-27B-UD-IQ4_XS.gguf}; RES=$R/res; L=$RES/logs; G=$RES/gate
mkdir -p "$L" "$G"
C=${C:-32768}; PORT=${PORT:-18761}; BC="taskset -c ${BC_CPUS:-0-2,6-8}"
UP=$R/bin/U; TK=$R/bin/T; XB=${XBIN:-$R/bin/X}
say() { echo "=== $(date +%T) $*"; }
busy() { pgrep -f 'cmake|nvcc|cicc|ptxas|cc1plus|ninja|gmake' > /dev/null; }
# NOWAIT=1: only for non-timing work (md5 gates, VRAM fill) while a build runs
while [ "${NOWAIT:-0}" != 1 ] && busy; do say "build running, waiting"; sleep 20; done
pid=
srv_stop() { [ -n "$pid" ] || return 0; kill "$pid" 2>/dev/null
    for _ in $(seq 30); do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
    kill -9 "$pid" 2>/dev/null; wait "$pid" 2>/dev/null; pid=; sleep 2; }
trap srv_stop EXIT
TFLAGS=(--spec-draft-vocab $R/draft_vocab_qwen38.txt --spec-draft-vocab-n 65536 --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs)
TENV=(LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_SERVER_CACHE_SHARE_MIN=1024 LLAMA_GPU_VERIFY=1 LLAMA_SERVER_REASONING_CONTROL=0)
srv() {  # arm log
    local arm=$1 log=$2
    local common=(-m "$M" -fit off -ngl 99 -t 4 -fa on -ctk q4_0 -ctv q4_0 -c "$C" -np 1 --jinja --cache-ram 8192
                  --reasoning-effort low --host 127.0.0.1 --port $PORT --no-webui
                  --spec-type draft-mtp --spec-draft-n-max ${DRAFT_N:-4} -ctkd q4_0 -ctvd q4_0)
    case $arm in
        U0) env LD_LIBRARY_PATH=$UP $BC ${NSYS:-} $UP/llama-server -m "$M" --host 127.0.0.1 --port $PORT --no-webui > "$log" 2>&1 & ;;
        U1) env LD_LIBRARY_PATH=$UP $BC ${NSYS:-} $UP/llama-server "${common[@]}" > "$log" 2>&1 & ;;
        T)  env LD_LIBRARY_PATH=$TK "${TENV[@]}" $BC ${NSYS:-} $TK/llama-server "${common[@]}" "${TFLAGS[@]}" > "$log" 2>&1 & ;;
        X)  env LD_LIBRARY_PATH=$XB "${TENV[@]}" ${XENV:-} $BC ${NSYS:-} $XB/llama-server "${common[@]}" "${TFLAGS[@]}" ${XARGS:-} > "$log" 2>&1 & ;;
    esac
    pid=$!
    for _ in $(seq 600); do
        curl -sf "http://127.0.0.1:$PORT/health" > /dev/null && return 0
        kill -0 "$pid" 2>/dev/null || { wait "$pid" 2>/dev/null; pid=; return 1; }
        sleep 1
    done
    srv_stop; return 1
}
vram() { nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1; }
vrec() { echo "{\"label\":\"$1\",\"vram_mb\":$(vram),\"t\":\"$(date +%T)\"}" >> "$L/vram.jsonl"; }
cmd=$1; shift
case $cmd in
    sweep)
        arm=$1 label=$2 seeds=${3:-1,2,3}
        say "sweep $label ($arm) seeds $seeds XENV=${XENV:-}"
        srv "$arm" "$L/$label.server.log" || { say "$label server failed"; tail -20 "$L/$label.server.log"; exit 1; }
        vrec "$label.loaded"
        (cd "$L" && $BC python3 $R/spec_sweep.py --label "$label" --port $PORT --temps 1.0 --seeds "$seeds" --tokens 400)
        [ "${MVS:-0}" = 1 ] && $BC python3 $R/copy_bench.py --label "$label" --port $PORT --set mvs --temps 0.0 --tokens 1024 --out "$L/copy_bench.jsonl"
        vrec "$label.end"; srv_stop ;;
    full)
        arm=$1 p=$2 label=qwen.$1.p$2
        say "full $label XENV=${XENV:-}"
        srv "$arm" "$L/$label.server.log" || { say "$label server failed"; tail -20 "$L/$label.server.log"; exit 1; }
        vrec "$label.loaded"
        nctx=$(curl -sf "http://127.0.0.1:$PORT/props" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("default_generation_settings",{}).get("n_ctx") or d.get("n_ctx"))' 2>/dev/null || echo "?")
        echo "{\"label\":\"$label\",\"n_ctx\":\"$nctx\"}" >> "$L/vram.jsonl"
        (cd "$L" && $BC python3 $R/spec_sweep.py --label "$label" --port $PORT --temps 1.0 --seeds 1,2,3 --tokens 400)
        if [ "$p" = 1 ]; then
            $BC python3 $R/copy_bench.py --label "$label" --port $PORT --set mvs --temps 0.0 --tokens 1024 --out "$L/copy_bench.jsonl"
            $BC python3 $R/long_bench.py --label "$label" --port $PORT --sizes ${LONG_SIZES:-512,16k} --out "$L/long.jsonl"
        fi
        vrec "$label.end"; srv_stop ;;
    lb)
        label=$1; shift; i=0
        base=(-m "$M" -ngl 99 -fa 1 -ctk q4_0 -ctv q4_0 -t 4 -o jsonl -p 512,4096 -n 128 -r 3)
        for a in "$@"; do
            i=$((i + 1)); out=$L/lb.$label.$a.r$i.jsonl
            case $a in
                U) env LD_LIBRARY_PATH=$UP $BC $UP/llama-bench "${base[@]}" > "$out" 2> "$out.err" ;;
                T) env LD_LIBRARY_PATH=$TK LLAMA_GPU_VERIFY=1 $BC $TK/llama-bench "${base[@]}" > "$out" 2> "$out.err" ;;
                X) env LD_LIBRARY_PATH=$XB LLAMA_GPU_VERIFY=1 ${XENV:-} $BC $XB/llama-bench "${base[@]}" > "$out" 2> "$out.err" ;;
            esac
            say "lb $label $a r$i: $(jq -r '"\(.n_prompt)/\(.n_gen) \((.avg_ts * 10 | round) / 10)"' "$out" | tr '\n' ' ')"
        done ;;
    gate)
        label=$1; arm=${GATE_ARM:-X}
        say "gate $label ($arm) XENV=${XENV:-}"
        srv "$arm" "$G/$label.server.log" || { say "gate server failed"; tail -20 "$G/$label.server.log"; exit 1; }
        (cd $R && $BC python3 gate_chat.py --label "$label" --port $PORT --out "$G/gate_chat.jsonl" > /dev/null)
        $BC python3 $R/copy_bench.py --label "$label" --port $PORT --set mvs --temps 0.0 --tokens 1024 --out "$G/copy_bench.jsonl"
        $BC python3 $R/copy_bench.py --label "$label" --port $PORT --set short --temps 0.0 --tokens 512 --out "$G/copy_bench.jsonl"
        srv_stop
        { jq -r --arg l "$label" 'select(.label == $l) | "\(.prompt) \(.temp) \(.md5)"' "$G/gate_chat.jsonl"
          jq -r --arg l "$label" 'select(.label == $l) | .set as $s | .prompts | to_entries[] | "\($s) \(.key) \(.value.md5 | join(","))"' "$G/copy_bench.jsonl"; } > "$G/md5.$label.txt"
        say "gate $label: $(wc -l < "$G/md5.$label.txt") rows, md5sum $(md5sum < "$G/md5.$label.txt" | cut -c1-8)" ;;
    fill)  # arm sizes: VRAM peak (0.2 s sampling) over long_bench requests near the max context
        arm=$1 sizes=$2 label=fill.$1.c$C
        say "fill $label sizes $sizes XENV=${XENV:-}"
        srv "$arm" "$L/$label.server.log" || { say "$label server failed"; tail -20 "$L/$label.server.log"; exit 1; }
        v0=$(vram)
        ( peak=0; while sleep 0.2; do v=$(vram); [ "$v" -gt "$peak" ] && { peak=$v; echo $peak > "$L/$label.peak"; }; done ) &
        sp=$!
        $BC python3 $R/long_bench.py --label "$label" --port $PORT --sizes "$sizes" --out "$L/long.jsonl"
        kill $sp; total=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
        echo "{\"label\":\"$label\",\"c\":$C,\"vram_loaded_mb\":$v0,\"vram_peak_mb\":$(cat "$L/$label.peak"),\"total_mb\":$total}" | tee -a "$L/vram.jsonl"
        srv_stop ;;
    prof)  # arm label: nsys session, capture one T=1 chat request (en-tech, 300 tok) + one mvs T=0 request
        arm=$1 label=$2; P=$RES/prof; mkdir -p $P
        say "prof $label ($arm) XENV=${XENV:-}"
        NSYS="nsys launch --session=$label -t cuda --cuda-graph-trace=node --cuda-memory-usage=false" srv "$arm" "$P/$label.server.log" \
            || { say "$label server failed"; tail -20 "$P/$label.server.log"; exit 1; }
        req() { curl -sf "http://127.0.0.1:$PORT/v1/chat/completions" -H 'Content-Type: application/json' -d "$1" | python3 -c 'import json,sys; t=json.load(sys.stdin)["timings"]; print(json.dumps({k: t.get(k) for k in ("predicted_n","predicted_ms","draft_n","draft_n_accepted")}))'; }
        chat='{"messages":[{"role":"user","content":"Explain how a B-tree index works in a relational database: node layout, search, insertion with splits, deletion with merges, and why it suits disks. Use a concrete example with numbers."}],"max_tokens":300,"temperature":1.0,"seed":1,"cache_prompt":false}'
        req "$chat" > /dev/null   # warmup (graphs captured)
        nsys start --session=$label -o $P/$label.chat -f true
        req "$chat" | tee $P/$label.chat.timings.json
        nsys stop --session=$label
        mvs=$(python3 -c 'import json; p=json.load(open("/root/copy_prompts.json"))["mvs"]; k=sorted(p)[0]; print(json.dumps({"messages":[{"role":"user","content":p[k]}],"max_tokens":512,"temperature":0.0,"seed":1,"cache_prompt":True,"chat_template_kwargs":{"enable_thinking":False}}))')
        req "$mvs" > /dev/null
        nsys start --session=$label -o $P/$label.mvs -f true
        req "$mvs" | tee $P/$label.mvs.timings.json
        nsys stop --session=$label
        srv_stop
        for f in chat mvs; do nsys export -t sqlite -f true -o $P/$label.$f.sqlite $P/$label.$f.nsys-rep > /dev/null 2>&1; done
        say "prof $label done" ;;
    proflong)  # arm label chars: nsys over one long_bench-style request (T=0+T=1, 256 tok); analyze with --skip-s past prefill
        arm=$1 label=$2 chars=$3; P=$RES/prof; mkdir -p $P
        say "proflong $label ($arm) c$chars XENV=${XENV:-}"
        NSYS="nsys launch --session=$label -t cuda --cuda-graph-trace=node --cuda-memory-usage=false" srv "$arm" "$P/$label.server.log" \
            || { say "$label server failed"; tail -20 "$P/$label.server.log"; exit 1; }
        $BC python3 $R/long_bench.py --label "$label.warm" --port $PORT --sizes 512 --out "$P/long.jsonl" > /dev/null
        nsys start --session=$label -o $P/$label.long -f true
        $BC python3 $R/long_bench.py --label "$label" --port $PORT --sizes c$chars --out "$P/long.jsonl"
        nsys stop --session=$label
        srv_stop
        nsys export -t sqlite -f true -o $P/$label.long.sqlite $P/$label.long.nsys-rep > /dev/null 2>&1
        say "proflong $label done" ;;
    long)  # arm label sizes: fresh server, long_bench only (LB_STREAM=0 for non-streaming requests)
        arm=$1 label=$2 sizes=$3
        say "long $label ($arm) $sizes stream=${LB_STREAM:-1} XENV=${XENV:-}"
        srv "$arm" "$L/$label.server.log" || { say "$label server failed"; tail -20 "$L/$label.server.log"; exit 1; }
        $BC python3 $R/long_bench.py --label "$label" --port $PORT --sizes "$sizes" --out "$L/long.jsonl"
        srv_stop ;;
    *) echo "unknown $cmd"; exit 2 ;;
esac
