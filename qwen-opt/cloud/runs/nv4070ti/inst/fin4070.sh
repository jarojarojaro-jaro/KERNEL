#!/usr/bin/env bash
# ON the box: CTX=<n> fin4070.sh — baseline U0/U1/T on Qwen3.8-27B UD-IQ3_XXS (nv-final layout, report 27/29 metrics).
# Order: llama-bench U T T U (pp512 + tg128 r3, KV q4_0), servers U0 U1 T (p1: chat T=1 6x3, chat T=0 s1, mvs T=0,
# long 512/16k) | T U1 U0 (p2: chat T=1 6x3, mvs T=0). Labels qwen.<arm>.p<n> as nvf_summary.py expects.
set -uo pipefail
. /root/cloud/lib4070.sh
arm() {  # arm pass
    local a=$1 p=$2 label=qwen.$1.p$2; local slog=$L/$label.server.log
    say "arm $label"
    srv "$a" "$slog" || { say "$label failed"; tail -20 "$slog"; return 0; }
    sleep 3; vram_row "$label" ",\"gpu_verify\":\"$([ "$a" = T ] && echo $TV || echo -)\""
    (cd "$L" && $BC python3 $H/spec_sweep.py --label "$label" --port $PORT --temps 1.0 --seeds 1,2,3 --tokens 400)
    [ "$p" = 1 ] && (cd "$L" && $BC python3 $H/spec_sweep.py --label "$label" --port $PORT --temps 0.0 --seeds 1 --tokens 400)
    $BC python3 $H/copy_bench.py --label "$label" --port $PORT --set mvs --temps 0.0 --tokens 1024 --out "$L/copy_bench.jsonl"
    [ "$p" = 1 ] && $BC python3 $H/long_bench.py --label "$label" --port $PORT --sizes 512,16k --out "$L/long.jsonl"
    echo "{\"label\":\"$label\",\"vram_peak_end_mb\":$(vram)}" >> "$L/vram.jsonl"
    srv_stop
    grep -h -E "draft acceptance rate" "$slog" 2>/dev/null | tail -1 || true
}
i=0
for a in U T T U; do
    i=$((i + 1)); out=$L/lb.qwen.$a.r$i.jsonl
    base=(-m "$GGUF" -ngl 99 -fa 1 -ctk q4_0 -ctv q4_0 -t 6 -p 512 -n 128 -r 3 -o jsonl)
    case $a in
        U) $BC $UP/llama-bench "${base[@]}" > "$out" 2> "$out.err" ;;
        T) env LLAMA_GPU_VERIFY=$TV $BC $TK/llama-bench "${base[@]}" > "$out" 2> "$out.err" ;;
    esac
    say "lb $a r$i: $(jq -r '"\(.n_prompt)/\(.n_gen) \((.avg_ts * 10 | round) / 10)"' "$out" | tr '\n' ' ')"
done
arm U0 1; arm U1 1; arm T 1
arm T 2;  arm U1 2; arm U0 2
touch "$RES/main.done"; say "fin4070 done"
