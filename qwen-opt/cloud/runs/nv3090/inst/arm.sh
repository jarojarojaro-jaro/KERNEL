#!/usr/bin/env bash
# ON the instance (nv-3090 round, 2026-10-20): arm.sh <label> <U0|U1|T|N> <bench,...> [VAR=val ...]
#   U0 upstream -m only | U1 upstream prod flags + MTP n=4 | T pkg cuda-topka2 (lookup W16 + share + GPU verify)
#   N  = T flags on /root/bin/$BIN (default nv0) plus the extra VAR=val switches.
# Benches (sweep.py rows -> $OUT/rows.jsonl): chat1 (T=1, $SEEDS), chat0 (T=0 s1), mvs (T=0), short (T=0),
#   gate (gate_chat.py + mvs + short T=0 md5 -> $OUT/gate.jsonl, $OUT/copy_gate.jsonl).
# Env: MODEL (gguf file in /root/models), CTX, SEEDS (default 1,2,3), OUT (default /root/results/nv3090/logs),
#   CPUS (server pinning, default 0-7), TV (LLAMA_GPU_VERIFY for T/N, default 1).
# VRAM: nvidia-smi polled every 200 ms while the server lives; max/after-load in $OUT/vram.jsonl.
set -uo pipefail
label=$1; a=$2; benches=$3; shift 3
H=/root/cloud; M=/root/models; PORT=18701
MODEL=${MODEL:?}; CTX=${CTX:?}; SEEDS=${SEEDS:-1,2,3}; OUT=${OUT:-/root/results/nv3090/logs}; CPUS=${CPUS:-0-7}
BIN=${BIN:-nv0}; TV=${TV:-1}
# DRAFT_N=<n> among the extra VAR=val args sets --spec-draft-n-max for U1/T/N (default 4)
DRAFT_N=4
for kv in "$@"; do case $kv in DRAFT_N=*) DRAFT_N=${kv#DRAFT_N=} ;; esac; done
mkdir -p "$OUT"; slog=$OUT/$label.server.log
gguf=$M/$MODEL
prod=(-m "$gguf" -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c "$CTX" -np 1 --jinja --cache-ram 16384
      --reasoning-effort low --host 127.0.0.1 --port $PORT --no-webui
      --spec-type draft-mtp --spec-draft-n-max $DRAFT_N -ctkd q4_0 -ctvd q4_0)
tflags=(--spec-draft-vocab $H/draft_vocab_qwen38.txt --spec-draft-vocab-n 65536
        --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs)
tenv=(LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_SERVER_CACHE_SHARE_MIN=1024 LLAMA_GPU_VERIFY=$TV
      LLAMA_SERVER_REASONING_CONTROL=0)
case $a in
    U0) cmd=(/root/bin/upstream/llama-server -m "$gguf" --host 127.0.0.1 --port $PORT --no-webui) ;;
    U1) cmd=(/root/bin/upstream/llama-server "${prod[@]}") ;;
    T)  cmd=(env "${tenv[@]}" "$@" /root/bin/topka2/llama-server "${prod[@]}" "${tflags[@]}") ;;
    N)  cmd=(env "${tenv[@]}" "$@" /root/bin/$BIN/llama-server "${prod[@]}" "${tflags[@]}") ;;
    *) echo "bad arm $a"; exit 2 ;;
esac
echo "=== $(date +%T) $label: ${cmd[*]}" | tee -a "$OUT/arms.log"
taskset -c "$CPUS" "${cmd[@]}" > "$slog" 2>&1 &
pid=$!
nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -lms 200 > "$OUT/$label.vram.txt" 2>/dev/null &
vpid=$!
stop() { kill $pid 2>/dev/null; for _ in $(seq 30); do kill -0 $pid 2>/dev/null || break; sleep 1; done
         kill -9 $pid 2>/dev/null; kill $vpid 2>/dev/null; wait 2>/dev/null; sleep 2; }
trap stop EXIT
ok=0
for _ in $(seq 600); do
    curl -sf "http://127.0.0.1:$PORT/health" > /dev/null && { ok=1; break; }
    kill -0 $pid 2>/dev/null || break
    sleep 1
done
[ $ok = 1 ] || { echo "$label: server failed"; tail -15 "$slog"; exit 1; }
sleep 2
vload=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
nctx=$(curl -sf "http://127.0.0.1:$PORT/props" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("default_generation_settings",{}).get("n_ctx") or d.get("n_ctx"))' 2>/dev/null)
cd $H
for b in ${benches//,/ }; do
    case $b in
        chat1) taskset -c "$CPUS" python3 sweep.py --label "$label" --port $PORT --set chat --temps 1.0 --seeds "$SEEDS" --tokens 400 --out "$OUT/rows.jsonl" ;;
        chat0) taskset -c "$CPUS" python3 sweep.py --label "$label" --port $PORT --set chat --temps 0.0 --tokens 400 --out "$OUT/rows.jsonl" ;;
        mvs)   taskset -c "$CPUS" python3 sweep.py --label "$label" --port $PORT --set mvs --temps 0.0 --tokens 1024 --out "$OUT/rows.jsonl" ;;
        short) taskset -c "$CPUS" python3 sweep.py --label "$label" --port $PORT --set short --temps 0.0 --tokens 512 --out "$OUT/rows.jsonl" ;;
        gate)  taskset -c "$CPUS" python3 gate_chat.py --label "$label" --port $PORT --out "$OUT/gate.jsonl" > /dev/null
               taskset -c "$CPUS" python3 sweep.py --label "$label" --port $PORT --set mvs --temps 0.0 --tokens 1024 --out "$OUT/copy_gate.jsonl"
               taskset -c "$CPUS" python3 sweep.py --label "$label" --port $PORT --set short --temps 0.0 --tokens 512 --out "$OUT/copy_gate.jsonl" ;;
        long)  taskset -c "$CPUS" python3 long_prompt.py --label "$label" --port $PORT --out "$OUT/long.jsonl" ;;
        *) echo "unknown bench $b" ;;
    esac
done
vmax=$(sort -n "$OUT/$label.vram.txt" | tail -1)
echo "{\"label\":\"$label\",\"arm\":\"$a\",\"model\":\"$MODEL\",\"ctx\":\"$CTX\",\"n_ctx\":\"$nctx\",\"vram_load\":$vload,\"vram_max\":${vmax:-0},\"extra\":\"$*\"}" | tee -a "$OUT/vram.jsonl"
grep -h -E "draft acceptance rate|CUDA error|out of memory" "$slog" | tail -3
