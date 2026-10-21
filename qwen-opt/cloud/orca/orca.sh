#!/usr/bin/env bash
# OrcaCyber-Nano-1.0 (qwen35, 65 blk, built-in MTP) on a rented RTX 3090 — baseline + optimization campaign.
# Runs ON the instance after setup-orca.sh. Order: KV/ctx budget -> baseline -> speculation space ->
# host/flag switches -> KV quant -> ctx ladder with long prompts -> llama-bench -> greedy md5 -> ABBA confirm.
# Every stage is time-guarded by /root/qwenbench-deadline; the GPU is never left idle between experiments.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
W=${W:-/root/w}; MODELS=${MODELS:-/root/models}
RES=${RESULTS:-/root/results}/$(date +%Y%m%d-%H%M)/orca-3090
PORT=${PORT:-18433}
KV=${KV:-q4_0}
BASE=$W/base/build/bin
FORK=$W/fork/build/bin
M=$MODELS/OrcaCyber-Nano-1.0-AI-Defense-Mix-15.7G.gguf
DF=$MODELS/OrcaCyber-Nano-1.0-AI-Defense-DFlash2-Q8_0.gguf
VOCAB=$HERE/draft_vocab_qwen38.txt
mkdir -p "$RES"/{logs,probe,sweep,long,lb,greedy}
servers=$RES/servers.jsonl

now() { date -u +%T; }
log() { echo "$(now) $*"; }
vram() { nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' '; }
deadline=$(cat /root/qwenbench-deadline 2>/dev/null || echo $(( $(date +%s) + 3 * 3600 )))
time_left() { [ "$(date +%s)" -lt $((deadline - 900)) ]; }

append_json() {  # FILE key=value ...
    local f=$1; shift
    python3 - "$f" "$@" <<'PY'
import json, sys
f, d = sys.argv[1], {}
for kv in sys.argv[2:]:
    k, _, v = kv.partition("=")
    if v in ("yes", "true"): v = True
    elif v in ("no", "false"): v = False
    else:
        for cast in (int, float):
            try: v = cast(v); break
            except ValueError: pass
    d[k] = v
open(f, "a").write(json.dumps(d) + "\n")
PY
}

# production host switches (CUDA build; the HIP/PM4 ones are inert and not set)
FORK_ENV="LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_SERVER_CACHE_SHARE_MIN=1024 \
LLAMA_GPU_VERIFY=1 LLAMA_SPEC_COUPLED=1 LLAMA_SERVER_YIELD_FAST=2 LLAMA_TOKENIZE_PAR=8 \
LLAMA_CKPT_VRAM=2 LLAMA_CHAT_NATIVE=0 LLAMA_SERVER_SAFE_SPECIAL=1 LLAMA_SERVER_SAFE_TOOLS=1 \
LLAMA_MTP_REQUANT_CACHE=/root/.cache/llama-mtp"

srv_pid=
srv_start() {  # label bin envstr args... -> writes one row to servers.jsonl, 0 = healthy
    local label=$1 bin=$2 envs=$3; shift 3
    local logf=$RES/logs/$label.log t0 error= none_ctx vram_mib
    pkill -9 -f "llama-server.*--port $PORT" 2>/dev/null || true
    for _ in $(seq 90); do [ "$(vram)" -lt 1500 ] 2>/dev/null && break; sleep 1; done
    t0=$(date +%s)
    # shellcheck disable=SC2086
    env $envs "$bin/llama-server" --host 127.0.0.1 --port "$PORT" --no-webui "$@" > "$logf" 2>&1 &
    srv_pid=$!
    local ok=no
    for _ in $(seq 900); do
        if curl -sf "http://127.0.0.1:$PORT/health" > /dev/null 2>&1; then ok=yes; break; fi
        kill -0 "$srv_pid" 2>/dev/null || break
        sleep 1
    done
    local load=$(( $(date +%s) - t0 ))
    if [ "$ok" != yes ]; then
        error=$(grep -iE 'failed to allocate|CUDA error|out of memory|error:|GGML_ASSERT|invalid|Permission denied|No such file' "$logf" | tail -2 | tr '\n' ' ' | cut -c1-300)
        [ -n "$error" ] || error=$(tail -1 "$logf" 2>/dev/null | cut -c1-200)
        kill -9 "$srv_pid" 2>/dev/null || true; wait "$srv_pid" 2>/dev/null || true; srv_pid=
        append_json "$servers" "label=$label" "ok=no" "load_s=$load" "error=$error" "args=$*"
        echo "$(now) FAIL $label (${load}s) $error"
        return 1
    fi
    none_ctx=$(grep -oE 'n_ctx[a-z_]*[[:space:]]*=[[:space:]]*[0-9]+' "$logf" | tail -1 | grep -oE '[0-9]+' || true)
    vram_mib=$(vram)
    append_json "$servers" "label=$label" "ok=yes" "load_s=$load" "n_ctx=$none_ctx" "vram_mib=$vram_mib" \
        "offload=$(grep -oE 'offloaded [0-9]+/[0-9]+ layers' "$logf" | tail -1)" \
        "kv_buf=$(grep -oE 'CUDA0 KV buffer size = [0-9.]+ MiB' "$logf" | tail -1)" \
        "args=$*"
    echo "$(now) OK   $label (${load}s, n_ctx=$none_ctx, VRAM=${vram_mib} MiB)"
    return 0
}

srv_stop() {
    [ -n "${srv_pid:-}" ] || return 0
    kill "$srv_pid" 2>/dev/null || true
    for _ in $(seq 30); do kill -0 "$srv_pid" 2>/dev/null || break; sleep 1; done
    kill -9 "$srv_pid" 2>/dev/null || true
    wait "$srv_pid" 2>/dev/null || true
    srv_pid=
}
trap 'srv_stop; [ -n "${mon_pid:-}" ] && kill "$mon_pid" 2>/dev/null || true' EXIT

spec_args() {  # mode n tree -> SPEC_ARGS
    local mode=$1 n=$2 tree=$3
    SPEC_ARGS=()
    case $mode in
        none) ;;
        mtp)  SPEC_ARGS=(--spec-type draft-mtp --spec-draft-n-max "$n" -ctkd "${DRAFT_KV:-$KV}" -ctvd "${DRAFT_KV:-$KV}")
              [ "$tree" = fork ] && [ "${MTP_EXTRAS:-1}" = 1 ] && SPEC_ARGS+=(--spec-draft-vocab "$VOCAB" \
                  --spec-draft-vocab-n "${VOCAB_N:-65536}" --spec-draft-head-type "${HEAD_TYPE:-iq4_xs}" \
                  --spec-mtp-type "${HEAD_TYPE:-iq4_xs}") ;;
        dflash) SPEC_ARGS=(-md "$DF" -ngld 99 --spec-type draft-dflash --spec-draft-n-max "$n") ;;
        *) echo "unknown mode $mode" >&2; return 1 ;;
    esac
    return 0
}

run_one() {  # label tree mode n kv ctx [env_extra] [cli_extra]
    local label=$1 tree=$2 mode=$3 n=$4 kv=$5 ctx=$6 envx=${7:-} cli=${8:-}
    time_left || return 1
    KV=$kv
    local bin=$FORK envs="$FORK_ENV"
    [ "$tree" = base ] && { bin=$BASE; envs=""; }
    spec_args "$mode" "$n" "$tree" || return 0
    local args=(-m "$M" -fa on -ctk "$kv" -ctv "$kv" -c "$ctx" -np 1 -ngl 999 -fit off --jinja)
    # shellcheck disable=SC2206
    [ -n "$cli" ] && args+=($cli)
    srv_start "$label" "$bin" "$envs $envx" "${args[@]}" "${SPEC_ARGS[@]}" || return 0
    ( cd "$RES/sweep" && python3 "$HERE/spec_sweep.py" --label "$label|$tree|$mode$n|$kv|$ctx" \
        --port "$PORT" --temps 1.0 --seeds 1,2 ) || true
    srv_stop
}

run_long() {  # label tree mode n kv ctx fracs [env_extra]
    local label=$1 tree=$2 mode=$3 n=$4 kv=$5 ctx=$6 fracs=$7 envx=${8:-}
    time_left || return 1
    KV=$kv
    local bin=$FORK envs="$FORK_ENV"
    [ "$tree" = base ] && { bin=$BASE; envs=""; }
    spec_args "$mode" "$n" "$tree" || return 0
    srv_start "$label" "$bin" "$envs $envx" -m "$M" -fa on -ctk "$kv" -ctv "$kv" -c "$ctx" -np 1 \
        -ngl 999 -fit off --jinja "${SPEC_ARGS[@]}" || return 0
    python3 "$HERE/orca_measure.py" long --port "$PORT" --label "$label" --ctx "$ctx" --fracs "$fracs" \
        --out "$RES/long/long.jsonl" || true
    srv_stop
}

probe_ctx() {  # ctx kv mode n -> usable?  (load + 0.8 depth prompt)
    local ctx=$1 kv=$2 mode=$3 n=$4
    local label="probe.$kv.$ctx.$mode$n"
    time_left || return 1
    KV=$kv
    spec_args "$mode" "$n" fork
    local t0 d ok=no depth=no actual
    t0=$(date +%s)
    if srv_start "$label" "$FORK" "$FORK_ENV" -m "$M" -fa on -ctk "$kv" -ctv "$kv" -c "$ctx" -np 1 \
        -ngl 999 -fit off --jinja "${SPEC_ARGS[@]}"; then
        actual=$(grep -oE 'n_ctx[a-z_]*[[:space:]]*=[[:space:]]*[0-9]+' "$RES/logs/$label.log" | tail -1 | grep -oE '[0-9]+')
        local frac
        frac=$(awk -v c="${actual:-$ctx}" 'BEGIN { f = 16384 / c; if (f > 0.5) f = 0.5; printf "%.6f", f }')
        d=$(python3 "$HERE/orca_measure.py" long --port "$PORT" --label "$label" --ctx "${actual:-$ctx}" \
            --fracs "$frac" --out "$RES/probe/long.jsonl" 2>/dev/null | tail -1) || true
        case "$d" in *'"ok": true'*) depth=yes ;; esac
        srv_stop
        [ "$depth" = yes ] && ok=yes
    fi
    append_json "$RES/probe/servers.jsonl" "label=$label" "requested_ctx=$ctx" "kv=$kv" "mode=$mode$n" \
        "n_ctx=${actual:-0}" "vram_mib=$(vram)" "load_s=$(( $(date +%s) - t0 ))" "depth_0.8=$depth" "ok=$ok"
    [ "$ok" = yes ]
}

# --- GPU monitor: proves the card is loaded during the campaign ---
nvidia-smi --query-gpu=timestamp,power.draw,power.limit,clocks.sm,memory.used,utilization.gpu,temperature.gpu \
    --format=csv -l 2 >> "$RES/gpu-monitor.csv" 2>/dev/null &
mon_pid=$!

log "campaign start; deadline $(date -u -d @$deadline '+%H:%M') UTC; results $RES"

# ============ 1. KV / context budget (the answer to "how much context fits") ============
MAXCTX=0
for ctx in 262144 229376 196608 163840 131072; do
    if probe_ctx "$ctx" q4_0 mtp 4; then MAXCTX=$ctx; log "max usable ctx (q4_0, MTP): $ctx"; break; fi
done
[ "$MAXCTX" = 0 ] && MAXCTX=65536
probe_ctx "$MAXCTX" q8_0 mtp 4 || true
probe_ctx "$MAXCTX" q4_0 dflash 6 || true
probe_ctx "$MAXCTX" f16 none 0 || true

# ============ 2. baseline: upstream vs fork, no spec vs MTP ============
run_one base.none.q4_0.32k   base none   0 q4_0 32768
run_one base.mtp4.q4_0.32k   base mtp    4 q4_0 32768
run_one fork.none.q4_0.32k   fork none   0 q4_0 32768
run_one fork.mtp4.q4_0.32k   fork mtp    4 q4_0 32768

# ============ 3. speculation space (fork, q4_0, 32k) ============
for n in 1 2 3 5 6 8; do run_one "fork.mtp$n.q4_0.32k" fork mtp "$n" q4_0 32768; done
for n in 2 4 8;     do run_one "fork.dflash$n.q4_0.32k" fork dflash "$n" q4_0 32768; done
run_one fork.dflash6.q4_0.32k fork dflash 6 q4_0 32768

# ============ 4. host/flag switches around the MTP baseline ============
run_one fork.mtp4.lookup0.q4_0.32k  fork mtp 4 q4_0 32768 "LLAMA_SPEC_LOOKUP=0"
run_one fork.mtp4.lookupw8.q4_0.32k fork mtp 4 q4_0 32768 "LLAMA_SPEC_LOOKUP_W=8"
run_one fork.mtp4.coupled0.q4_0.32k fork mtp 4 q4_0 32768 "LLAMA_SPEC_COUPLED=0"
run_one fork.mtp4.verify0.q4_0.32k  fork mtp 4 q4_0 32768 "LLAMA_GPU_VERIFY=0"
run_one fork.mtp4.ckpt0.q4_0.32k    fork mtp 4 q4_0 32768 "LLAMA_CKPT_VRAM=0"
run_one fork.mtp4.safe0.q4_0.32k    fork mtp 4 q4_0 32768 "LLAMA_SERVER_SAFE_SPECIAL=0 LLAMA_SERVER_SAFE_TOOLS=0"
MTP_EXTRAS=0 run_one fork.mtp4.novocab.q4_0.32k fork mtp 4 q4_0 32768
VOCAB_N=131072 run_one fork.mtp4.vocab128k.q4_0.32k fork mtp 4 q4_0 32768
HEAD_TYPE=q8_0 run_one fork.mtp4.headq8.q4_0.32k fork mtp 4 q4_0 32768
for v in GGML_CUDA_FORCE_MMQ=1 GGML_CUDA_MMQ_PREC=1 GGML_OP_OFFLOAD_MIN_BATCH=32; do
    run_one "fork.mtp4.$(echo "$v" | tr '=.' '__').q4_0.32k" fork mtp 4 q4_0 32768 "$v"
done

# ============ 5. KV quant (fork, MTP n=4, 32k) ============
run_one fork.mtp4.q8_0.32k fork mtp 4 q8_0 32768
run_one fork.mtp4.f16.32k  fork mtp 4 f16  32768

# ============ 6. llama-bench: raw kernels, base vs fork ============
if time_left; then
    for tree in base fork; do
        for kv in q4_0 q8_0; do
            bin=$BASE; [ "$tree" = fork ] && bin=$FORK
            [ -x "$bin/llama-bench" ] || continue
            "$bin/llama-bench" -m "$M" -p 512 -n 128 -r 5 -o jsonl -fa on -ctk "$kv" -ctv "$kv" -ngl 999 \
                > "$RES/lb/$tree.$kv.jsonl" 2> "$RES/logs/lb.$tree.$kv.log" || true
            log "llama-bench $tree $kv done"
        done
    done
fi

# ============ 7. long context: TTFT + decode at depth, all the way to MAXCTX ============
run_long "long.mtp4.q4_0.32768" fork mtp 4 q4_0 32768 0.5,0.8
run_long "long.mtp4.q8_0.32768" fork mtp 4 q8_0 32768 0.5
run_long "long.mtp4.f16.32768"  fork mtp 4 f16  32768 0.5
run_long "long.mtp4.q4_0.131072" fork mtp 4 q4_0 131072 0.25
run_long "long.dflash6.q4_0.131072" fork dflash 6 q4_0 131072 0.25 || true
run_long "long.mtp4.q4_0.$MAXCTX" fork mtp 4 q4_0 "$MAXCTX" 0.125 || true
run_long "long.base.mtp4.q4_0.131072" base mtp 4 q4_0 131072 0.25 || true

# ============ 8. greedy md5 determinism (drafter must not change the output) ============
if time_left; then
    printf 'label\tmd5\n' > "$RES/greedy/md5.tsv"
    for cfg in "base:none:0" "fork:none:0" "fork:mtp:4" "fork:dflash:6"; do
        IFS=: read -r tree mode n <<<"$cfg"
        time_left || break
        KV=q4_0
        bin=$FORK; envs="$FORK_ENV"; [ "$tree" = base ] && { bin=$BASE; envs=""; }
        spec_args "$mode" "$n" "$tree"
        label="md5.$tree.$mode$n"
        srv_start "$label" "$bin" "$envs" -m "$M" -fa on -ctk q4_0 -ctv q4_0 -c 8192 -np 1 -ngl 999 \
            -fit off --jinja "${SPEC_ARGS[@]}" || continue
        h=$(python3 "$HERE/orca_measure.py" md5 --port "$PORT" --label "$label" --out "$RES/greedy/$label.txt" | tail -1) || true
        srv_stop
        printf '%s\t%s\n' "$label" "$h" >> "$RES/greedy/md5.tsv"
        log "md5 $label = $h"
    done
fi

# ============ 9. ABBA confirm of the best configs until 15 min before the deadline ============
if time_left; then
    best=$(python3 - "$RES/sweep/spec_sweep.jsonl" <<'PY'
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
rows.sort(key=lambda r: -r["median_tps"])
seen, out = set(), []
for r in rows:
    lab = r["label"].split("|")[0]
    if lab not in seen:
        seen.add(lab); out.append(lab)
    if len(out) == 3: break
print(" ".join(out))
PY
) || best=
    log "ABBA confirm of: $best"
    for round in 1; do
        for lab in $best; do
            time_left || break 2
            tree=${lab%%.*}; rest=${lab#*.}
            mode_n=${rest%%.*}; rest2=${rest#*.}
            kv=${rest2%%.*}; ctxs=${rest2#*.}
            mode=$(sed -E 's/^([a-z]+)[0-9]*$/\1/' <<<"$mode_n")
            n=$(sed -E 's/^[a-z]+([0-9]*)$/\1/' <<<"$mode_n"); n=${n:-0}
            case $ctxs in *k) ctx=$(( ${ctxs%k} * 1024 )) ;; *) ctx=$ctxs ;; esac
            run_one "abba$round.${lab}" "$tree" "$mode" "$n" "$kv" "$ctx"
        done
    done
fi

# ============ 10. wave 2: extra switches around the single best config ============
if time_left; then
    top=$(python3 - "$RES/sweep/spec_sweep.jsonl" <<'PY'
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
rows = [r for r in rows if not r["label"].startswith("abba")]
rows.sort(key=lambda r: -r["median_tps"])
print(rows[0]["label"].split("|")[0] if rows else "")
PY
) || true
    if [ -n "$top" ]; then
        tree=${top%%.*}; rest=${top#*.}
        mode_n=${rest%%.*}; rest2=${rest#*.}
        kv=${rest2%%.*}; ctxs=${rest2#*.}
        mode=$(sed -E 's/^([a-z]+)[0-9]*$/\1/' <<<"$mode_n")
        n=$(sed -E 's/^[a-z]+([0-9]*)$/\1/' <<<"$mode_n"); n=${n:-0}
        case $ctxs in *k) ctx=$(( ${ctxs%k} * 1024 )) ;; *) ctx=$ctxs ;; esac
        log "wave2 around $top (tree $tree, $mode n=$n, $kv, ctx $ctx)"
        run_one "w2.$top.graphopt"  "$tree" "$mode" "$n" "$kv" "$ctx" "GGML_CUDA_GRAPH_OPT=1"
        run_one "w2.$top.novmm"     "$tree" "$mode" "$n" "$kv" "$ctx" "GGML_CUDA_NO_VMM=1"
        run_one "w2.$top.ub1024"    "$tree" "$mode" "$n" "$kv" "$ctx" "" "-b 2048 -ub 1024"
        run_one "w2.$top.ub2048"    "$tree" "$mode" "$n" "$kv" "$ctx" "" "-ub 2048"
        [ "$mode" != none ] && run_one "w2.$top.pmin03" "$tree" "$mode" "$n" "$kv" "$ctx" "" "--spec-draft-p-min 0.3"
        [ "$mode" != none ] && run_one "w2.$top.pmin06" "$tree" "$mode" "$n" "$kv" "$ctx" "" "--spec-draft-p-min 0.6"
        run_one "w2.$top.chain0"    "$tree" "$mode" "$n" "$kv" "$ctx" "LLAMA_MTP_CHAIN_SCHED=0"
        run_one "w2.$top.kvmask0"   "$tree" "$mode" "$n" "$kv" "$ctx" "LLAMA_KV_MASK_FAST=0"
        run_one "w2.$top.lazysave0" "$tree" "$mode" "$n" "$kv" "$ctx" "LLAMA_SPEC_LAZY_SAVE=0"
        run_one "w2.$top.async0"    "$tree" "$mode" "$n" "$kv" "$ctx" "LLAMA_ASYNC_INPUTS=0"
        run_one "w2.$top.fasttopk0" "$tree" "$mode" "$n" "$kv" "$ctx" "LLAMA_SAMPLER_FAST_TOPK=0"
        VOCAB_N=32768 run_one "w2.$top.vocab32k" "$tree" "$mode" "$n" "$kv" "$ctx"
        HEAD_TYPE=q4_K run_one "w2.$top.headq4k" "$tree" "$mode" "$n" "$kv" "$ctx"
        DRAFT_KV=q8_0 run_one "w2.$top.draftkv8" "$tree" "$mode" "$n" "$kv" "$ctx"
    fi
fi

python3 "$HERE/orca_measure.py" summary --dir "$RES" > "$RES/summary.txt" 2>&1 || true
log "campaign done: $RES"
