# kqb.sh: shared steps of the build-item jobs K-028, K-040, K-049, K-052, K-130 (KqBuild, 2026-11-24). Sourced only.
# Every step stops :8080 first (chat8080.sh stop); the .jobs file ends with chat8080.sh restore. Test ports 18794/18796,
# server and clients under taskset -c 2-5. A = production ~/llama-topka (topka-q70 3191b25f4), B = the item's build.
# The item script sets: K, B_BIN (dir with llama-server/llama-bench), B_LIB (ROCm lib dir for B), B_ROOT (ROCM_DIR for
# run-topka.sh / xtxbench: bin/ + lib/), PM4 env.
#   md5_gate          fresh-start greedy T=0 (fusion/greedy.sh, Qwen UD-Q4_K_XL, plain + MTP n4, ctx 8192, :18794)
#                     vs the production references plain c4708318 / MTP 6f14e814 -> out/$K.md5.PASS
#   bench_abba ARGS   llama-bench A B B A (production model, -fa 1, KV $KVARGS), only after md5 PASS
#   xtx_ab ARGS       xtxbench t1 A = production vs B = $B_ROOT (restart arms, both PM4 as set in $XTX_ENV), md5 of
#                     the fresh-start rounds vs A inside xtxbench, only after md5 PASS
PROD=$HOME/llama-topka
A_BIN=$PROD/bin
A_LIB=/opt/rocm/core-10.0/lib
M=$HOME/models/orca/Qwen3.8-27B-Uncensored-Q4_K_M.gguf
KQ=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
OUT=$KQ/out; mkdir -p "$OUT"
PY=$HOME/qwen-opt/.venv/bin/python
KVARGS=${KVARGS:--ctk q4_0 -ctv q4_0}

need_build() {
    [ -x "$B_BIN/llama-server" ] || [ -x "$B_BIN/llama-bench" ] || { echo "$K: no build in $B_BIN, nothing to test"; exit 3; }
}

need_pass() {
    [ -f "$OUT/$K.md5.PASS" ] || { echo "$K $1: skipped (no md5 PASS in $OUT)"; exit 0; }
}

md5_gate() {
    rm -f "$OUT/$K.md5.PASS"
    ~/qwen-opt/l1tok/chat8080.sh stop
    ~/qwen-opt/lookup/vram_ok.sh || { echo "$K md5: VRAM busy"; return 1; }
    PORT=18794 timeout 600 taskset -c 2-5 ~/qwen-opt/fusion/greedy.sh "$B_BIN" "$B_BIN:$B_LIB" "$OUT/$K-md5" qwen > /dev/null
    local bad=0 f m want
    for f in "$OUT/$K-md5.plain.txt" "$OUT/$K-md5.mtp.txt"; do
        [ -s "$f" ] || { echo "$K md5 ${f##*/}: missing or empty (see ${f%.txt}.log)"; bad=1; continue; }
        m=$(md5sum < "$f" | cut -c1-8)
        case $f in *.mtp.txt) want=6f14e814 ;; *) want=c4708318 ;; esac
        if [ "$m" = "$want" ]; then echo "$K md5 ${f##*/}: $m OK"; else echo "$K md5 ${f##*/}: $m MISMATCH (want $want)"; bad=1; fi
    done
    if [ $bad = 0 ]; then touch "$OUT/$K.md5.PASS"; echo "RESULT $K md5: PASS"; else echo "RESULT $K md5: FAIL"; return 1; fi
}

bench_abba() {
    need_pass bench
    ~/qwen-opt/l1tok/chat8080.sh stop
    local args=("$@") j=$OUT/$K-bench.jsonl arm bin lib n=0
    [ ${#args[@]} -gt 0 ] || args=(-p 4096 -n 128 -r 3)
    : > "$j"
    for arm in A B B A; do
        n=$((n + 1))
        if [ $arm = A ]; then bin=$A_BIN lib=$A_LIB; else bin=$B_BIN lib=$B_LIB; fi
        echo "== $K bench $arm$n: $bin"
        # shellcheck disable=SC2086
        LD_LIBRARY_PATH=$bin:$lib timeout 200 taskset -c 2-5 "$bin/llama-bench" -m "$M" -ngl 999 -fa 1 $KVARGS \
            "${args[@]}" -o jsonl 2> "$OUT/$K-bench-$arm$n.err" | sed "s/^{/{\"arm\":\"$arm\",\"round\":$n,/" | tee -a "$j"
    done
    python3 - "$j" "$K" <<'EOF'
import json, sys, collections
rows = [json.loads(l) for l in open(sys.argv[1]) if l.startswith("{")]
by = collections.defaultdict(list)
for r in rows:
    by[(f"pp{r['n_prompt']}" if r["n_prompt"] else f"tg{r['n_gen']}", r["arm"])].append(r["avg_ts"])
for t in sorted({k[0] for k in by}):
    a, b = by.get((t, "A"), []), by.get((t, "B"), [])
    if a and b:
        ma, mb = sum(a) / len(a), sum(b) / len(b)
        print(f"RESULT {sys.argv[2]} bench {t}: A {ma:.2f} B {mb:.2f} t/s ({100 * (mb / ma - 1):+.2f}%) "
              f"A {['%.2f' % x for x in a]} B {['%.2f' % x for x in b]}")
    else:
        print(f"RESULT {sys.argv[2]} bench {t}: incomplete (A {len(a)} B {len(b)} rounds)")
EOF
}

xtx_ab() {
    need_pass xtxbench
    local e envs=()
    for e in ${XTX_ENV:-GGML_HIP_PM4=0}; do envs+=(--base-env "$e" --var-env "$e"); done
    # xtxbench stops :8080 itself (ONE SIGTERM, 60 s, SIGKILL) and restores run-topka.sh uncensored on exit; port 18794
    cd ~/qwen-opt/xtxbench && timeout 840 "$PY" xtxbench.py t1 --label "$K" --base "$PROD" --var "$B_ROOT" "${envs[@]}" \
        --snap-compat --t0 none --depths 1700 "$@"
}
