#!/usr/bin/env bash
# Kernel A/B on the rented RTX 3090 (OrcaCyber-Nano-1.0):  MMVQ rows per block (n1 / multi-column), ubatch prefill,
# and the effect on the spec server. Runs ON the instance after setup-orca.sh.
#   kernel.sh [stage...]     stages: lb, srv, long, correct   (default: all)
set -u
B=/root/w/fork/build/bin
M=/root/models/OrcaCyber-Nano-1.0-AI-Defense-Mix-15.7G.gguf
VOCAB=/root/cloud/draft_vocab_qwen38.txt
PORT=18433
RES=/root/results/$(date +%Y%m%d-%H%M)/kernel-3090
mkdir -p "$RES"/{lb,sweep,long,logs}
export LD_LIBRARY_PATH=$B
stages=${*:-lb srv long correct}

vram() { nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' '; }
stop() { pkill -9 -f "llama[-]server.*--port $PORT" 2>/dev/null; sleep 2; }
now() { date -u +%T; }

lb_one() {  # label env...
    local label=$1; shift
    env "$@" $B/llama-bench -m "$M" -p 512 -n 128 -r 5 -fa on -ctk q4_0 -ctv q4_0 -ngl 999 -o jsonl \
        > "$RES/lb/$label.jsonl" 2> "$RES/logs/lb.$label.log"
    python3 - "$RES/lb/$label.jsonl" "$label" <<'PY'
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
pp = next((r["avg_ts"] for r in rows if r.get("n_prompt", 0) > 1), 0)
tg = next((r["avg_tg"] if "avg_tg" in r else r["avg_ts"] for r in rows if r.get("n_gen", 0) > 1), 0)
print(f"{sys.argv[2]:28s} pp512={pp:7.1f}  tg128={tg:6.2f}")
PY
}

srv_sweep() {  # label "ENV=1 ENV2=2" [extra server args...]
    local label=$1 envs=$2; shift 2
    stop
    env LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_SERVER_CACHE_SHARE_MIN=1024 LLAMA_GPU_VERIFY=1 \
        LLAMA_SPEC_COUPLED=1 LLAMA_SERVER_YIELD_FAST=2 LLAMA_TOKENIZE_PAR=8 LLAMA_CKPT_VRAM=2 \
        LLAMA_CHAT_NATIVE=0 LLAMA_SERVER_SAFE_SPECIAL=1 LLAMA_SERVER_SAFE_TOOLS=1 $envs \
        $B/llama-server --host 127.0.0.1 --port $PORT --no-webui -m "$M" -fa on -ctk q4_0 -ctv q4_0 \
        -c "${CTX:-32768}" -np 1 -ngl 999 -fit off --jinja --spec-type draft-mtp --spec-draft-n-max "${N:-2}" \
        -ctkd q4_0 -ctvd q4_0 --spec-draft-vocab "$VOCAB" --spec-draft-vocab-n 65536 \
        --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs "$@" > "$RES/logs/srv.$label.log" 2>&1 &
    local ok=no
    for _ in $(seq 300); do curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 && { ok=yes; break; }; sleep 1; done
    if [ "$ok" = no ]; then echo "$label: server failed ($(tail -1 "$RES/logs/srv.$label.log" | cut -c1-120))"; stop; return 1; fi
    local v; v=$(vram)
    ( cd "$RES/sweep" && python3 /root/cloud/spec_sweep.py --label "$label|fork|mtp${N:-2}|q4_0|${CTX:-32768}" \
        --port $PORT --temps 1.0 --seeds 1,2 ) | tail -1
    echo "   VRAM=${v} MiB"
    stop
}

long_one() {  # label ub
    local label=$1 ub=$2
    stop
    env LLAMA_SPEC_LOOKUP=3 LLAMA_GPU_VERIFY=1 LLAMA_SPEC_COUPLED=1 LLAMA_CKPT_VRAM=2 LLAMA_CHAT_NATIVE=0 \
        LLAMA_SERVER_SAFE_SPECIAL=1 LLAMA_SERVER_SAFE_TOOLS=1 \
        $B/llama-server --host 127.0.0.1 --port $PORT --no-webui -m "$M" -fa on -ctk q4_0 -ctv q4_0 \
        -c 32768 -np 1 -ngl 999 -fit off --jinja -b "$ub" -ub "$ub" --spec-type draft-mtp --spec-draft-n-max 2 \
        -ctkd q4_0 -ctvd q4_0 --spec-draft-vocab "$VOCAB" --spec-draft-vocab-n 65536 \
        --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs > "$RES/logs/long.$label.log" 2>&1 &
    local ok=no
    for _ in $(seq 300); do curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 && { ok=yes; break; }; sleep 1; done
    if [ "$ok" = no ]; then echo "$label: server failed"; stop; return 1; fi
    python3 /root/cloud/orca_measure.py long --port $PORT --label "prefill.$label" --ctx 32768 --fracs 0.5,0.8 \
        --tokens 64 --out "$RES/long/long.jsonl"
    stop
}

echo "$(now) kernel A/B start -> $RES"

if [[ " $stages " == *" lb "* ]]; then
    lb_one rows0 GGML_CUDA_MMVQ_N1_ROWS=0
    lb_one rows2 GGML_CUDA_MMVQ_N1_ROWS=2
    lb_one rows4 GGML_CUDA_MMVQ_N1_ROWS=4
    lb_one n1_2_m4 GGML_CUDA_MMVQ_N1_ROWS=2 GGML_CUDA_MMVQ_MROWS=4
fi

if [[ " $stages " == *" srv "* ]]; then
    srv_sweep base_rows0 "GGML_CUDA_MMVQ_N1_ROWS=0"
    srv_sweep n1rows2 "GGML_CUDA_MMVQ_N1_ROWS=2"
    srv_sweep mrows4 "GGML_CUDA_MMVQ_MROWS=4"
    srv_sweep n1rows2_mrows4 "GGML_CUDA_MMVQ_N1_ROWS=2 GGML_CUDA_MMVQ_MROWS=4"
fi

conc_one() {  # np requests label
    local np=$1 req=$2 label=$3
    stop
    env LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_GPU_VERIFY=1 LLAMA_SPEC_COUPLED=1 \
        LLAMA_SERVER_YIELD_FAST=2 LLAMA_CKPT_VRAM=2 LLAMA_CHAT_NATIVE=0 \
        LLAMA_SERVER_SAFE_SPECIAL=1 LLAMA_SERVER_SAFE_TOOLS=1 \
        $B/llama-server --host 127.0.0.1 --port $PORT --no-webui -m "$M" -fa on -ctk q4_0 -ctv q4_0 \
        -c 32768 -np "$np" -ngl 999 -fit off --jinja --spec-type draft-mtp --spec-draft-n-max 2 \
        -ctkd q4_0 -ctvd q4_0 --spec-draft-vocab "$VOCAB" --spec-draft-vocab-n 65536 \
        --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs > "$RES/logs/conc.$label.log" 2>&1 &
    local ok=no
    for _ in $(seq 300); do curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 && { ok=yes; break; }; sleep 1; done
    if [ "$ok" = no ]; then echo "$label: server failed"; stop; return 1; fi
    python3 /root/cloud/conc.py --port $PORT --label "$label" --requests "$req" --tokens 400 --out "$RES/conc.jsonl"
    stop
}

if [[ " $stages " == *" rollback "* ]]; then
    srv_sweep rb_default "LLAMA_GDN_REPLAY=1 LLAMA_CONV_LAG=1"
    srv_sweep rb_noreplay "LLAMA_GDN_REPLAY=0"
    srv_sweep rb_noconvlag "LLAMA_CONV_LAG=0"
    srv_sweep rb_both0 "LLAMA_GDN_REPLAY=0 LLAMA_CONV_LAG=0"
fi

if [[ " $stages " == *" conc "* ]]; then
    conc_one 1 1 np1_req1
    conc_one 2 2 np2_req2
fi

if [[ " $stages " == *" long "* ]]; then
    long_one ub512 512
    long_one ub1024 1024
    long_one ub2048 2048
fi

if [[ " $stages " == *" correct "* ]]; then
    GGML_CUDA_MMVQ_N1_ROWS=2 GGML_CUDA_MMVQ_MROWS=4 \
        $B/test-backend-ops -o MUL_MAT -b CUDA0 -p "iq4_xs" > "$RES/logs/correct.log" 2>&1
    tail -2 "$RES/logs/correct.log"
fi

python3 /root/cloud/orca_measure.py summary --dir "$RES" > "$RES/summary.txt" 2>&1 || true
echo "$(now) kernel A/B done"
