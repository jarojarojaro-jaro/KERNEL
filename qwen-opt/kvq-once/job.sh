#!/bin/bash
# 66-SYNTEZA items 1-3 on the final chat config (Qwen3.8-27B-Uncensored Q4_K_M, ctx 262144, KV q4_0, MTP n4, eco 2200):
#   N = ~/wt/kvq-once/build-hip (branch kvq-once off topka-q63 c0576e3e8): GGML_HIP_KVQ_ONCE=1 (one block per 2 Q tiles,
#       K/V fetched and V dequantized once per MTP verify, bit-exact by construction), split knobs
#       GGML_HIP_KVQ_BLOCKS_PER_SM / GGML_HIP_KVQ_MIN_SPLIT; P = production ~/llama-topka. Every server: run-topka.sh uncensored.
# Stages (STAGES, default all, in this order):
#   check   test-backend-ops FLASH_ATTN_EXT q4_0 vs CPU (ONCE 0 and 1) + fa_hash ONCE 0 vs 1 (bit-exact) -> gate for ONCE arms
#   kperf   test-backend-ops perf, D 256 GQA 6, kv 2048/32768/98304/196608, nb 1/5: ONCE 0 1 1 0 + split sweep
#           BLOCKS_PER_SM {1,2,3,4} x MIN_SPLIT {-,64,128,256} x ONCE {0,1}
#   md5     servers P N1 N1 P: spec_sweep T=1 seeds 1,2,3 + greedy md5 (baseline 0221afd9); N0: greedy md5
#   long    servers N0 N1 N1 N0: lc.py 1.7k/94k/199k T=0 256 tokens: decode t/s + text md5 per depth
#   hostgap server P with LLAMA_HOSTGAP_TRACE=16: lc.py 1.7k/94k/199k -> host timeline of the decode step per depth
#   prof    servers N0 and N1 under rocprofv3 (PM4 off: tapes are invisible to it): lc.py 1.7k/94k/199k -> per step
#           GPU time, FA share (kvq + combine), H2D copies; kill line: FA at 199k not -10% or better with ONCE
# Restores the chat server with run-topka.sh uncensored (health + n_ctx 262144) on exit. Run ONLY from run-jobs.sh.
set -u
W=~/wt/kvq-once; N=$W/build-hip; P=~/llama-topka; here=~/qwen-opt/kvq-once
out=$here/run-$(date +%m%d-%H%M); mkdir -p "$out"
port=18792; py=~/qwen-opt/.venv/bin/python
STAGES=${STAGES:-check,kperf,md5,long,hostgap,prof}
export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0; unset QUEUE_PM4_SAFETY
log() { echo "$*" | tee -a "$out/summary.txt"; }
on() { case ",$STAGES," in *,$1,*) return 0 ;; esac; return 1; }

restore() {
  pkill -f "llama-server.*--port $port( |$)" 2>/dev/null
  if ! pgrep -f "llama-server.*--port 8080( |$)" >/dev/null; then
    setsid nohup ~/qwen-opt/run-topka.sh uncensored > "$out/restore.out" 2>&1 < /dev/null &
    for _ in $(seq 240); do curl -sf 127.0.0.1:8080/health >/dev/null && break; sleep 1; done
  fi
  log "restore: health=$(curl -s 127.0.0.1:8080/health) n_ctx=$(curl -s 127.0.0.1:8080/props | python3 -c 'import json,sys; print(json.load(sys.stdin)["default_generation_settings"]["n_ctx"])' 2>/dev/null)"
}
trap restore EXIT
trap 'exit 1' TERM INT

# ONE SIGTERM, wait up to $2 s (default 60), then SIGKILL; $3: pgrep pattern of the server process (default by port)
stop_port() {
  local p; p=$(pgrep -f "${3:-llama-server.*--port $1( |$)}" | head -1)
  [ -z "$p" ] && return 0
  kill -TERM "$p"; for _ in $(seq "${2:-60}"); do kill -0 "$p" 2>/dev/null || return 0; sleep 1; done
  kill -KILL "$p"; log "port $1: SIGKILL needed"; sleep 2
}
stop_port 8080
/usr/local/sbin/xtx-eco status > "$out/eco.txt" 2>&1
grep -q 'sclk cap (state): 2200' "$out/eco.txt" || { log "ECO 2200 NOT ACTIVE: $(head -1 "$out/eco.txt")"; exit 1; }
log "kvq-once job $(date -u +%FT%TZ) N=$(git -C $W rev-parse --short HEAD) stages=$STAGES out=$out"

# server ARM-LABEL BIN [K=V ...]: fresh run-topka.sh uncensored on $port with the extra env
srv() {
  local label=$1 bin=$2; shift 2
  "$HOME/qwen-opt/lookup/vram_ok.sh" || { log "$label: VRAM busy"; return 1; }
  env "$@" ROCM_DIR="$bin" PORT=$port LOG="$out/srv-$label.log" ~/qwen-opt/run-topka.sh uncensored > "$out/srv-$label.out" 2>&1 &
  for _ in $(seq 300); do curl -sf 127.0.0.1:$port/health >/dev/null && return 0; sleep 1; done
  log "$label: server not healthy"; tail -5 "$out/srv-$label.out" | tee -a "$out/summary.txt"; stop_port $port; return 1
}
greedy_md5() {
  curl -s -m 300 127.0.0.1:$port/v1/chat/completions -H 'Content-Type: application/json' \
    -d '{"messages":[{"role":"user","content":"Explain how a hash map works, step by step."}],"max_tokens":256,"temperature":0,"seed":1}' \
    | python3 -c 'import json,sys,hashlib; print(hashlib.md5(json.load(sys.stdin)["choices"][0]["message"]["content"].encode()).hexdigest()[:8])'
}
tbo() { ( export GGML_HIP_PM4=0; LD_LIBRARY_PATH=$N/bin:/opt/rocm/core-10.0/lib taskset -c 2-5 env "$@" ); }

once_ok=1
# ---------------------------------------------------------------- check
if on check; then
  for o in 0 1; do
    tbo GGML_HIP_KVQ_ONCE=$o $N/bin/test-backend-ops -o FLASH_ATTN_EXT -b ROCm0 -p 'type_K=q4_0,type_V=q4_0' > "$out/tbo-once$o.txt" 2>&1
    grep -h FAIL "$out/tbo-once$o.txt" | grep -o 'FLASH_ATTN_EXT([^)]*)' | sort -u > "$out/tbo-fail$o.txt"
    log "test-backend-ops FA q4_0 ONCE=$o: $(grep -E 'tests passed' "$out/tbo-once$o.txt" | tail -1)"
  done
  new=$(comm -13 "$out/tbo-fail0.txt" "$out/tbo-fail1.txt")
  grep -q 'tests passed' "$out/tbo-once1.txt" && [ -z "$new" ] || { once_ok=0; log "CHECK FAIL: new failures with ONCE=1: $new"; }
  for kv in 4096 98304 196608; do for nb in 1 3 5 8 10 16; do
    h0=$(tbo GGML_HIP_KVQ_ONCE=0 $here/fa_hash ROCm0 $kv $nb 2>&1 | grep -o 'hash=[0-9a-f]*')
    h1=$(tbo GGML_HIP_KVQ_ONCE=1 $here/fa_hash ROCm0 $kv $nb 2>&1 | grep -o 'hash=[0-9a-f]*')
    s=same; [ -n "$h0" ] && [ "$h0" = "$h1" ] || { s=DIFF; once_ok=0; }
    log "fa_hash kv=$kv nb=$nb ONCE0 $h0 ONCE1 $h1 $s"
  done; done
  [ $once_ok = 1 ] && log "CHECK PASS: ONCE=1 bit-identical to ONCE=0 on all fa_hash shapes, no new test-backend-ops failures"
fi

# ---------------------------------------------------------------- kperf
if on kperf; then
  filt='hsk=256,hsv=256,nh=4,nr23=\[6,1\],kv=(2048|32768|98304|196608),nb=(1|5),'
  perf() { # tag K=V...
    local tag=$1; shift
    tbo "$@" $N/bin/test-backend-ops perf -o FLASH_ATTN_EXT -b ROCm0 -p "$filt" 2>&1 | grep -E 'FLASH_ATTN_EXT\(' \
      | sed -E 's/.*kv=([0-9]+),nb=([0-9]+),.* ([0-9.]+) us\/run.*/\1 \2 \3/' | sed "s/^/$tag /" >> "$out/kperf.txt"
  }
  for o in 0 1 1 0; do [ $o = 1 ] && [ $once_ok = 0 ] && continue; perf "abba once=$o bps=- min=-" GGML_HIP_KVQ_ONCE=$o; done
  for b in 1 2 3 4; do for m in - 64 128 256; do for o in 0 1; do
    [ $o = 1 ] && [ $once_ok = 0 ] && continue
    e=(GGML_HIP_KVQ_ONCE=$o GGML_HIP_KVQ_BLOCKS_PER_SM=$b); [ $m != - ] && e+=(GGML_HIP_KVQ_MIN_SPLIT=$m)
    perf "sweep once=$o bps=$b min=$m" "${e[@]}"
  done; done; done
  python3 - "$out/kperf.txt" <<'EOF' | tee -a "$out/summary.txt"
import sys, statistics as st
from collections import defaultdict
d = defaultdict(list)
for l in open(sys.argv[1]):
    kind, o, b, m, kv, nb, us = l.split()
    d[(o, b, m, int(kv), int(nb))].append(float(us))
base = {k[3:]: st.mean(v) for k, v in d.items() if k[:3] == ("once=0", "bps=-", "min=-")}
print("kperf FA us/run (mean), vs default (once=0, 2 blocks/SM, no min split):")
shapes = sorted(base)
print(f"{'config':<28}" + "".join(f"{f'{kv//1024}k nb{nb}':>15}" for kv, nb in shapes))
for cfg in sorted({k[:3] for k in d}):
    row = []
    for s in shapes:
        v = d.get(cfg + s)
        row.append(f"{st.mean(v):8.1f} {100*(st.mean(v)/base[s]-1):+5.1f}%" if v else f"{'-':>15}")
    print(f"{' '.join(cfg):<28}" + "".join(f"{x:>15}" for x in row))
for once in ("once=0", "once=1"):
    c = [(st.mean([st.mean(d[k]) / base[k[3:]] for k in d if k[:3] == cfg and k[3] >= 32768 and k[4] == 5]), cfg)
         for cfg in {k[:3] for k in d} if cfg[0] == once]
    if c:
        r, cfg = min(c)
        print(f"best {once} on nb5 >= 32k: {' '.join(cfg)} {100*(r-1):+.1f}% vs default (split change = order of sums: KLD gate before adoption)")
EOF
fi

# ---------------------------------------------------------------- md5 + spec_sweep
if on md5; then
  i=0
  for arm in P N1 N1 P N0; do
    [ $arm = N1 ] && [ $once_ok = 0 ] && continue
    case $arm in P) b=$P; e=(X=0) ;; N0) b=$N; e=(GGML_HIP_KVQ_ONCE=0) ;; N1) b=$N; e=(GGML_HIP_KVQ_ONCE=1) ;; esac
    i=$((i + 1)); lab=md5-$arm-$i; srv $lab $b "${e[@]}" || continue
    if [ $arm != N0 ]; then
      r=$(cd ~/qwen-opt && taskset -c 2-5 $py spec_sweep.py --label "kvq-$lab" --port $port --temps 1.0 --seeds 1,2,3 | tail -1)
      echo "spec $arm $r" >> "$out/sweep.txt"; log "spec_sweep $arm: $r"
    fi
    log "md5 $arm $(greedy_md5) (baseline 0221afd9)"
    stop_port $port
  done
  python3 - "$out/sweep.txt" <<'EOF' | tee -a "$out/summary.txt"
import re, sys, statistics as st
d = {}
for l in open(sys.argv[1]):
    m = re.search(r"^spec (\w+) .*median\s+([\d.]+) t/s,\s+([\d.]+) ms/step", l)
    if m: d.setdefault(m[1], []).append((float(m[2]), float(m[3])))
if "P" in d and "N1" in d:
    a, b = [st.mean(x[0] for x in d[k]) for k in ("P", "N1")]
    sa, sb = [st.mean(x[1] for x in d[k]) for k in ("P", "N1")]
    print(f"spec_sweep T=1 P {a:.1f} t/s {sa:.2f} ms/step -> ONCE {b:.1f} t/s {sb:.2f} ms/step: {100*(b/a-1):+.2f}% t/s, {100*(sb/sa-1):+.2f}% ms/step")
EOF
fi

# ---------------------------------------------------------------- long context ABBA
if on long && [ $once_ok = 1 ]; then
  i=0
  for arm in N0 N1 N1 N0; do
    i=$((i + 1)); o=${arm#N}; lab=long-$arm-$i
    srv $lab $N GGML_HIP_KVQ_ONCE=$o || continue
    taskset -c 2-5 $py $here/lc.py --port $port --label $lab --out "$out/lc.jsonl" --depths 1700,94000,199000 | tee -a "$out/long.txt"
    stop_port $port
  done
  python3 - "$out/lc.jsonl" <<'EOF' | tee -a "$out/summary.txt"
import json, sys, statistics as st
from collections import defaultdict
d = defaultdict(list)
for l in open(sys.argv[1]):
    r = json.loads(l)
    if r["label"].startswith("long-"):
        d[(r["label"].split("-")[1], r["depth"])].append(r)
for depth in sorted({k[1] for k in d}):
    a, b = d.get(("N0", depth), []), d.get(("N1", depth), [])
    if not a or not b: continue
    ta, tb = st.mean(r["decode_tps"] for r in a), st.mean(r["decode_tps"] for r in b)
    ma, mb = st.mean(r["ms_step"] for r in a), st.mean(r["ms_step"] for r in b)
    md5 = {r["md5"] for r in a + b}
    print(f"long {depth:>6}: decode {ta:.2f} -> {tb:.2f} t/s ({100*(tb/ta-1):+.2f}%), {ma:.2f} -> {mb:.2f} ms/step, "
          f"prefill {st.mean(r['prefill_tps'] for r in a):.0f}/{st.mean(r['prefill_tps'] for r in b):.0f} t/s, "
          f"md5 {'IDENTICAL ' + md5.pop() if len(md5) == 1 else 'DIFFERENT ' + ','.join(sorted(md5))}")
EOF
fi

# ---------------------------------------------------------------- host timeline (item 1)
if on hostgap; then
  if srv hg $P LLAMA_HOSTGAP_TRACE=16; then
    taskset -c 2-5 $py $here/lc.py --port $port --label hg --out "$out/lc.jsonl" --depths 1700,94000,199000 | tee -a "$out/long.txt"
    stop_port $port
    python3 $here/hg_parse.py "$out/srv-hg.out" --depths 1700,94000,199000 | tee -a "$out/summary.txt"
  fi
fi

# ---------------------------------------------------------------- rocprofv3 step profile (item 1 + kill line)
if on prof; then
  for arm in N0 N1; do
    [ $arm = N1 ] && [ $once_ok = 0 ] && continue
    pb=$out/profbin-$arm; mkdir -p $pb/bin
    printf '#!/bin/bash\nexec /opt/rocm/core-10.0/bin/rocprofv3 --kernel-trace --memory-copy-trace --output-format csv -d %s -o run -- %s "$@"\n' \
      "$out/prof-$arm" "$N/bin/llama-server" > $pb/bin/llama-server; chmod +x $pb/bin/llama-server
    srv prof-$arm $pb GGML_HIP_PM4=0 GGML_HIP_KVQ_ONCE=${arm#N} || continue
    taskset -c 2-5 $py $here/lc.py --port $port --label prof-$arm --out "$out/lc.jsonl" --depths 1700,94000,199000 | tee -a "$out/long.txt"
    # the tracer writes its CSV at exit; signal the traced server itself (rocprofv3 may run it as a child)
    stop_port $port 300 "^$N/bin/llama-server .*--port $port( |$)"
    for _ in $(seq 300); do pgrep -f "llama-server.*--port $port( |$)" >/dev/null || break; sleep 1; done
    stop_port $port
    log "rocprofv3 $arm (PM4 off, ms per verify step):"
    python3 $here/prof_step.py "$out/prof-$arm" "$out/lc.jsonl" prof-$arm | tee -a "$out/summary.txt" "$out/prof-$arm.txt"
    find "$out/prof-$arm" -name '*.csv' -size +20M -exec gzip {} \;
  done
  python3 - "$out/prof-N0.txt" "$out/prof-N1.txt" <<'EOF' 2>/dev/null | tee -a "$out/summary.txt"
import sys
def rows(f):
    r = {}
    for l in open(f):
        p = l.split()
        if p and p[0].isdigit() and len(p) > 6: r[int(p[0])] = (float(p[4]) + float(p[5]), float(p[2]))
    return r
a, b = rows(sys.argv[1]), rows(sys.argv[2])
for d in sorted(set(a) & set(b)):
    fa0, fa1 = a[d][0], b[d][0]
    print(f"prof FA (kvq+combine) at {d}: {fa0:.2f} -> {fa1:.2f} ms/step ({100*(fa1/fa0-1):+.1f}%), step {a[d][1]:.2f} -> {b[d][1]:.2f} ms")
d = max(set(a) & set(b), default=None)
if d is not None:
    ch = 100 * (b[d][0] / a[d][0] - 1)
    print(f"KILL LINE (FA at {d} must drop >= 10%): {ch:+.1f}% -> {'PASS' if ch <= -10 else 'KILL'}")
EOF
fi
log "done $(date -u +%FT%TZ); results $out"
