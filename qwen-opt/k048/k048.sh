#!/usr/bin/env bash
# K-048: prefill micro-batch -ub 1024 vs the production 512, Qwen3.8-27B-Uncensored Q4_K_M on ~/llama-topka. Queue only.
#   md5    production config on :18795 (srv.sh, ctx 262144), fresh server per arm, order 512 1024 1024 512:
#          kvq-once/lc.py 12k-token prompt + summary, T=0, 256 tokens -> md5 + prefill t/s; VRAM after start / after
#          the request (the -ub compute buffer is allocated at start; the K-033 poll records the peak)
#   bench  llama-bench pp4096 with -ub 512,1024 then 1024,512 (-r 5), PM4 off, FA D256 var 83 as production
# The 255k fill with -ub 1024 is NOT run (OOM risk: 1193 MiB free at 255k with ub 512, ctx262/run-262144).
set -u
here=$(cd "$(dirname "$0")" && pwd); . "$here/srv.sh"
out=$here/out; mkdir -p "$out"
py=$HOME/qwen-opt/.venv/bin/python
~/qwen-opt/l1tok/chat8080.sh stop
bash ~/qwen-opt/k033/dpm_poll.sh "$out/dpm-$1.txt" & poll=$!
trap 'kill $poll 2>/dev/null; srv_stop nowait' EXIT
case $1 in
md5)
    i=0
    for ub in 512 1024 1024 512; do
        i=$((i + 1)); arg=(); [ $ub = 1024 ] && arg=(EXTRA_ARGS=-ub,1024)
        srv_start "$out/md5-$i-ub$ub" "${arg[@]}" || continue
        v0=$(vram_mib)
        taskset -c 2-5 "$py" ~/qwen-opt/kvq-once/lc.py --port $PORT --label "ub$ub-$i" --out "$out/md5.jsonl" --depths 12000
        echo "ub $ub run $i: VRAM after start $v0 MiB, after the request $(vram_mib) MiB;" \
             "$(grep -ohE 'n_ubatch +[=:] *[0-9]+' "$out/md5-$i-ub$ub".{log,out} 2>/dev/null | head -1)"
        srv_stop
    done
    "$py" - "$out/md5.jsonl" <<'PY'
import json, sys
for r in map(json.loads, open(sys.argv[1])):
    print({k: r.get(k) for k in ("label", "depth", "prefill_tps", "decode_tps", "md5")})
PY
    ;;
bench)
    M=$HOME/models/orca/Qwen3.8-27B-Uncensored-Q4_K_M.gguf
    for order in 512,1024 1024,512; do
        GGML_HIP_PM4=0 GGML_HIP_FA_D256_VAR=83 LD_LIBRARY_PATH=$HOME/llama-topka/bin:/opt/rocm/core-10.0/lib \
            ~/llama-topka/bin/llama-bench -m "$M" -ngl 999 -fa 1 -ctk q4_0 -ctv q4_0 -p 4096 -n 0 -b 2048 -ub $order \
            -r 5 -o md 2>&1 | grep -E '^\|'
    done ;;
*) echo "usage: k048.sh md5|bench" >&2; exit 2 ;;
esac
kill $poll
nice python3 ~/qwen-opt/k033/dpm_sum.py "$out/dpm-$1.txt"
