#!/usr/bin/env bash
# KLD canaries: prove the KLD gate (kld_gate.py) detects real damage. LFM2.5-24B-A2B Q5_K_M, wikitext-2 test,
# 3 x 16384-token chunks, ubatch 1 (decode kernels), against the f16-KV reference logits REF (see kld-canary.md).
#
# usage: kld_canary.sh [--dry-run] [run|prep|gate|all|clean|list] [VARIANT...]     (default: all, every variant)
#   prep   CPU only: write the damaged model copies (perturb_gguf.py / llama-quantize) to CANARY_MODELS
#   run    GPU: one llama-perplexity per variant -> RESULTS/<variant>.log (resume: skips logs that parse);
#          deletes a variant's model copy after its log is complete (KEEP_MODELS=1 keeps it)
#   gate   table variant | expected | mean KLD | same top | verdict | OK/UNEXPECTED (kld_gate.py table)
#   all    per variant prep -> run -> delete copy (one 17 GB copy on disk at a time), then gate
#   clean  delete CANARY_MODELS/*.gguf;  list  variants with expectation and arguments
# exit: 0 all expectations met; 1 a canary passed / a control failed; 2 missing or errored logs; 3 refused
# env: BIN MODEL KLD_DIR REF TEXT ANCHOR RESULTS CANARY_MODELS PY GGUF_PY CHUNKS TIMEOUT PAUSE KEEP_MODELS
#      QUANT_THREADS GATE_K GATE_TAIL
set -euo pipefail

SELF=$(readlink -f "$0")
HERE=$(dirname "$SELF")
SERVER_RE='llama-server.*--port 8080'

# Runs inside both locks: refuse when the production server is up, then exec the command.
if [ "${1:-}" = _guarded ]; then
    shift
    if pgrep -f "$SERVER_RE" >/dev/null; then
        echo "kld_canary: llama-server on port 8080 is running, refusing GPU run" >&2
        exit 97
    fi
    exec "$@"
fi

BIN=${BIN:-$HOME/llama-opt/bin}
MODEL=${MODEL:-$HOME/models/lfm/LFM2.5-24B-A2B-Q5_K_M.gguf}
KLD_DIR=${KLD_DIR:-$HOME/wt/lfm3-prof}
REF=${REF:-$KLD_DIR/ref.kld}
TEXT=${TEXT:-$KLD_DIR/wikitext-2-raw/wiki.test.raw}
ANCHOR=${ANCHOR-$KLD_DIR/kld_q8kvq.log}  # accepted incumbent (q8_0 KV, kvq kernel); empty: baseline not gated
RESULTS=${RESULTS:-$HOME/qwen-opt/kld-canary}
CANARY_MODELS=${CANARY_MODELS:-$HOME/qwen-opt/kld-canary/models}  # throwaway broken copies, never in ~/models
PY=${PY:-$HOME/qwen-opt/.venv-kt/bin/python}
GGUF_PY=${GGUF_PY:-$HOME/llama-master/gguf-py}
CHUNKS=${CHUNKS:-3}
TIMEOUT=${TIMEOUT:-900}
PAUSE=${PAUSE:-45}
QUANT_THREADS=${QUANT_THREADS:-4}
GATE_K=${GATE_K:-2}
GATE_TAIL=${GATE_TAIL:-1.25}
LIBS=$BIN:$BIN/../lib:/opt/rocm/core-10.0/lib

DRY=0
if [ "${1:-}" = --dry-run ]; then DRY=1; shift; fi
MODE=${1:-all}
[ $# -gt 0 ] && shift
case $MODE in run|prep|gate|all|clean|list) ;; *) echo "unknown mode $MODE" >&2; exit 64 ;; esac

ALL_VARIANTS=(baseline baseline2 ctl_vec kv_q4 kv_k8v4 kv_k4v8 moe_k3 eps_x100 rope_p1 rope_p5
              wdown_p0.5 wdown_p2 wdown_p10 wattn_p0.5 wattn_p2 wattn_p10 q4km q3km)
VARIANTS=("$@")
[ ${#VARIANTS[@]} -eq 0 ] && VARIANTS=("${ALL_VARIANTS[@]}")

WDOWN='blk\.10\.ffn_down_exps\.weight'  # Q6_K, all 64 experts of MoE layer 10
WATTN='blk\.10\.attn_output\.weight'    # Q5_K, attention layer 10

# define VARIANT -> EXP NOTE BASE CTK CTV ENVS XARGS MDL PREP (perturb|quant|"") TENSOR DELTA QTYPE
define() {
    EXP=; NOTE=; BASE=$RESULTS/baseline.log; CTK=q8_0; CTV=q8_0; ENVS=(); XARGS=(); MDL=$MODEL
    PREP=; TENSOR=; DELTA=; QTYPE=
    case $1 in
        baseline)   EXP=PASS; NOTE="production q8_0 KV vs ANCHOR"; BASE=${ANCHOR:--}
                    [ "$BASE" = - ] && EXP=BASE ;;
        baseline2)  EXP=IDENTICAL; NOTE="same command again: determinism" ;;
        ctl_vec)    EXP=PASS; NOTE="old q8_0 vec kernel (known 0.044171)"; ENVS=(GGML_HIP_KVQ_Q8=0) ;;
        kv_q4)      EXP=FAIL; NOTE="q4_0 KV (known 0.128359)"; CTK=q4_0; CTV=q4_0 ;;
        kv_k8v4)    EXP=FAIL; NOTE="K q8_0, V q4_0 (vec kernel, f16 fallback)"; CTV=q4_0 ;;
        kv_k4v8)    EXP=FAIL; NOTE="K q4_0, V q8_0 (vec kernel, f16 fallback)"; CTK=q4_0 ;;
        moe_k3)     EXP=FAIL; NOTE="experts per token 4 -> 3"; XARGS=(--override-kv lfm2moe.expert_used_count=int:3) ;;
        eps_x100)   EXP=PROBE; NOTE="RMS-norm eps 1e-5 -> 1e-3"
                    XARGS=(--override-kv lfm2moe.attention.layer_norm_rms_epsilon=float:1e-3) ;;
        rope_p1)    EXP=PROBE; NOTE="rope freq base 1e7 +1%"; XARGS=(--rope-freq-base 10100000) ;;
        rope_p5)    EXP=PROBE; NOTE="rope freq base 1e7 +5%"; XARGS=(--rope-freq-base 10500000) ;;
        wdown_p0.5) EXP=PROBE; NOTE="blk.10 ffn_down_exps x1.005"; PREP=perturb; TENSOR=$WDOWN; DELTA=0.005 ;;
        wdown_p2)   EXP=PROBE; NOTE="blk.10 ffn_down_exps x1.02";  PREP=perturb; TENSOR=$WDOWN; DELTA=0.02 ;;
        wdown_p10)  EXP=FAIL;  NOTE="blk.10 ffn_down_exps x1.10";  PREP=perturb; TENSOR=$WDOWN; DELTA=0.10 ;;
        wattn_p0.5) EXP=PROBE; NOTE="blk.10 attn_output x1.005";   PREP=perturb; TENSOR=$WATTN; DELTA=0.005 ;;
        wattn_p2)   EXP=PROBE; NOTE="blk.10 attn_output x1.02";    PREP=perturb; TENSOR=$WATTN; DELTA=0.02 ;;
        wattn_p10)  EXP=FAIL;  NOTE="blk.10 attn_output x1.10";    PREP=perturb; TENSOR=$WATTN; DELTA=0.10 ;;
        q4km)       EXP=PROBE; NOTE="requantized Q5_K_M -> Q4_K_M"; PREP=quant; QTYPE=Q4_K_M ;;
        q3km)       EXP=FAIL;  NOTE="requantized Q5_K_M -> Q3_K_M"; PREP=quant; QTYPE=Q3_K_M ;;
        *) echo "unknown variant $1 (known: ${ALL_VARIANTS[*]})" >&2; exit 64 ;;
    esac
    [ -n "$PREP" ] && MDL=$CANARY_MODELS/$1.gguf
    return 0
}
for v in "${VARIANTS[@]}"; do define "$v"; done  # validate names before doing anything

show() { printf '%q ' "$@"; }
log_ok() { [ -f "$1" ] && python3 "$HERE/kld_gate.py" check "$1" 2>/dev/null; }
free_bytes() { df --output=avail -B1 "$1" | awk 'NR == 2 { print $1 }'; }

prep_variant() {  # $1 variant (define'd); returns 1 on failure
    [ -z "$PREP" ] && return 0
    if [ -f "$MDL" ]; then echo "[$1] model copy exists: $MDL"; return 0; fi
    local cmd
    if [ "$PREP" = perturb ]; then
        cmd=(flock -s /tmp/quiet.lock nice -n 10 env "PYTHONPATH=$GGUF_PY" "$PY" "$HERE/perturb_gguf.py" --verify
             "$MODEL" "$MDL" --tensor "$TENSOR" --delta "$DELTA")
    else
        cmd=(env HIP_VISIBLE_DEVICES=-1 "LD_LIBRARY_PATH=$LIBS" flock -s /tmp/quiet.lock nice -n 10
             "$BIN/llama-quantize" --allow-requantize "$MODEL" "$MDL.part" "$QTYPE" "$QUANT_THREADS")
    fi
    if [ $DRY = 1 ]; then
        echo "mkdir -p $(printf %q "$CANARY_MODELS")"
        show "${cmd[@]}"; echo
        [ "$PREP" = quant ] && echo "mv $(printf %q "$MDL.part") $(printf %q "$MDL")"
        return 0
    fi
    mkdir -p "$CANARY_MODELS"
    if [ "$PREP" = quant ]; then
        local need=$(( $(stat -c %s "$MODEL") + 10 * 1024 ** 3 ))
        if [ "$(free_bytes "$CANARY_MODELS")" -lt $need ]; then
            echo "[$1] not enough free space in $CANARY_MODELS" >&2; return 1
        fi
    fi
    echo "[$1] prep: $(show "${cmd[@]}")"
    if [ "$PREP" = quant ]; then
        "${cmd[@]}" > "$MDL.log" 2>&1 || { echo "[$1] llama-quantize failed, see $MDL.log" >&2; rm -f "$MDL.part"; return 1; }
        mv "$MDL.part" "$MDL"
    else
        "${cmd[@]}" || { echo "[$1] perturb_gguf.py failed" >&2; return 1; }
    fi
}

GPU_RUNS=0
run_variant() {  # $1 variant (define'd); returns 1 on failure
    local log=$RESULTS/$1.log
    if [ $DRY = 0 ] && log_ok "$log"; then echo "[$1] done: $log"; return 0; fi
    if [ $DRY = 0 ] && [ ! -f "$MDL" ]; then echo "[$1] model missing: $MDL (run prep)" >&2; return 1; fi
    local cmd=(env "${ENVS[@]}" "LD_LIBRARY_PATH=$LIBS" flock /tmp/gpu.lock flock /tmp/quiet.lock
               "$SELF" _guarded timeout "$TIMEOUT" "$BIN/llama-perplexity" -m "$MDL" -f "$TEXT" -ngl 99 -fa on
               -c 16384 -b 16384 -ub 1 --chunks "$CHUNKS" -ctk "$CTK" -ctv "$CTV"
               --kl-divergence-base "$REF" --kl-divergence "${XARGS[@]}")
    if [ $DRY = 1 ]; then
        [ $GPU_RUNS -gt 0 ] && echo "sleep $PAUSE"
        echo "pgrep -f '$SERVER_RE' && exit 3"
        echo "$(show "${cmd[@]}")> $(printf %q "$log.part") 2>&1 && mv $(printf %q "$log.part") $(printf %q "$log")"
        [ -n "$PREP" ] && [ "${KEEP_MODELS:-0}" != 1 ] && echo "rm $(printf %q "$MDL")"
        GPU_RUNS=$((GPU_RUNS + 1))
        return 0
    fi
    [ $GPU_RUNS -gt 0 ] && sleep "$PAUSE"
    if pgrep -f "$SERVER_RE" >/dev/null; then
        echo "kld_canary: llama-server on port 8080 is running, refusing GPU runs" >&2
        exit 3
    fi
    mkdir -p "$RESULTS"
    echo "[$1] run ($NOTE): $(show "${cmd[@]}")"
    GPU_RUNS=$((GPU_RUNS + 1))
    local rc=0
    "${cmd[@]}" > "$log.part" 2>&1 || rc=$?
    [ $rc = 97 ] && { rm -f "$log.part"; exit 3; }
    if [ $rc = 0 ] && log_ok "$log.part"; then
        mv "$log.part" "$log"
        python3 "$HERE/kld_gate.py" compare "$BASE" "$log" 2>/dev/null | tail -n 1 | sed "s/^/[$1] /" || true
        if [ -n "$PREP" ] && [ "${KEEP_MODELS:-0}" != 1 ]; then rm -f "$MDL"; fi
        return 0
    fi
    mv "$log.part" "$RESULTS/$1.err.log"
    echo "[$1] llama-perplexity failed (exit $rc), see $RESULTS/$1.err.log" >&2
    return 1
}

gate() {
    local manifest=$RESULTS/manifest.tsv cmd=(python3 "$HERE/kld_gate.py" table --k "$GATE_K" --tail-ratio "$GATE_TAIL")
    if [ $DRY = 1 ]; then
        echo "# write $manifest (name, expected, base log, candidate log, note), then:"
        show "${cmd[@]}" "$manifest"; echo
        return 0
    fi
    mkdir -p "$RESULTS"
    : > "$manifest"
    for v in "${VARIANTS[@]}"; do
        define "$v"
        printf '%s\t%s\t%s\t%s\t%s\n' "$v" "$EXP" "$BASE" "$RESULTS/$v.log" "$NOTE" >> "$manifest"
    done
    "${cmd[@]}" "$manifest"
}

check_inputs() {
    local f missing=0
    for f in "$BIN/llama-perplexity" "$MODEL" "$REF" "$TEXT"; do
        [ -e "$f" ] || { echo "missing: $f" >&2; missing=1; }
    done
    return $missing
}

case $MODE in
    list)
        for v in "${VARIANTS[@]}"; do
            define "$v"
            printf '%-11s %-9s %s | -ctk %s -ctv %s %s %s\n' "$v" "$EXP" "$NOTE" "$CTK" "$CTV" "${ENVS[*]}" "${XARGS[*]}"
        done ;;
    clean)
        if [ $DRY = 1 ]; then echo "rm -f $(printf %q "$CANARY_MODELS")/*.gguf"; else rm -fv "$CANARY_MODELS"/*.gguf; fi ;;
    prep)
        fail=0
        for v in "${VARIANTS[@]}"; do define "$v"; prep_variant "$v" || fail=1; done
        exit $fail ;;
    run)
        [ $DRY = 1 ] || check_inputs
        fail=0
        for v in "${VARIANTS[@]}"; do define "$v"; run_variant "$v" || fail=2; done
        exit $fail ;;
    gate)
        gate ;;
    all)
        [ $DRY = 1 ] || check_inputs
        fail=0
        for v in "${VARIANTS[@]}"; do
            define "$v"
            if [ $DRY = 0 ] && log_ok "$RESULTS/$v.log"; then echo "[$v] done: $RESULTS/$v.log"; continue; fi
            prep_variant "$v" && run_variant "$v" || fail=2
        done
        rc=0; gate || rc=$?
        [ $rc = 0 ] && rc=$fail
        exit $rc ;;
esac
