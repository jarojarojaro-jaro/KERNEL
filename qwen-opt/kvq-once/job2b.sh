#!/bin/bash
# kvq-once follow-up (2026-11-07, Main): GGML_HIP_KVQ_ONCE=2 (K dequantized once per warp pair as well, commit 47b6be451)
# vs ONCE=1 vs default, final chat config (Uncensored Q4_K_M, ctx 262144, KV q4_0, MTP n4, eco 2200). Stages:
#   build   relink ~/wt/kvq-once/build-hip (the fattn-kvq object is compiled; seconds)
#   check   test-backend-ops FA q4_0 ONCE=2 vs CPU + fa_hash ONCE 0 vs 2 (bit-exact) -> gate
#   kperf   test-backend-ops perf D 256 GQA 6 kv 32768/98304/196608 nb 1/5, ONCE 0 1 2 2 1 0
#   pmc     rocprofv3 --pmc DRAM read counter per kvq dispatch (nb 5 at 98k/196k, nb 1 at 196k), ONCE 0/1/2:
#           KV read amplification = bytes read / q4_0 K+V bytes
#   md5     servers P N2 N2 P: greedy md5 (baseline 0221afd9) + spec_sweep T=1
#   long    servers N0 N2 N2 N0: lc.py 199k (LONG_DEPTHS) T=0 256 tokens: decode t/s + text md5
# Restores the chat server with run-topka.sh uncensored (health + n_ctx 262144) on exit. Run ONLY from run-jobs.sh.
set -u
W=~/wt/kvq-once; N=$W/build-hip; P=~/llama-topka; here=~/qwen-opt/kvq-once
out=$here/run2b-$(date +%m%d-%H%M); mkdir -p "$out"
port=18792; py=~/qwen-opt/.venv/bin/python
O=2
STAGES=${STAGES:-build,check,kperf,pmc,md5,long}
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
log "kvq-once2 job $(date -u +%FT%TZ) N=$(git -C $W rev-parse --short HEAD) stages=$STAGES out=$out"

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
# ---------------------------------------------------------------- build (link only)
if on build; then
  nice -n 19 taskset -c 0-1 cmake --build $W/build-hip -j2 --target llama-server test-backend-ops > "$out/build.txt" 2>&1 \
    || { log "BUILD FAILED"; tail -5 "$out/build.txt" | tee -a "$out/summary.txt"; exit 1; }
  log "build: $(grep -cE 'Building|Linking' "$out/build.txt") steps, HEAD $(git -C $W rev-parse --short HEAD)"
fi
# ---------------------------------------------------------------- check
if on check; then
  tbo GGML_HIP_KVQ_ONCE=$O $N/bin/test-backend-ops -o FLASH_ATTN_EXT -b ROCm0 -p 'type_K=q4_0,type_V=q4_0' > "$out/tbo-once$O.txt" 2>&1
  log "test-backend-ops FA q4_0 ONCE=$O: $(grep -E 'tests passed' "$out/tbo-once$O.txt" | tail -1)"
  grep -qE '([0-9]+)/\1 tests passed' "$out/tbo-once$O.txt" || { once_ok=0; log "CHECK FAIL: test-backend-ops"; grep FAIL "$out/tbo-once$O.txt" | head -5 | tee -a "$out/summary.txt"; }
  for kv in 4096 98304 196608; do for nb in 1 3 5 8 10 16; do
    h0=$(tbo GGML_HIP_KVQ_ONCE=0 $here/fa_hash ROCm0 $kv $nb 2>&1 | grep -o 'hash=[0-9a-f]*')
    h1=$(tbo GGML_HIP_KVQ_ONCE=$O $here/fa_hash ROCm0 $kv $nb 2>&1 | grep -o 'hash=[0-9a-f]*')
    s=same; [ -n "$h0" ] && [ "$h0" = "$h1" ] || { s=DIFF; once_ok=0; }
    log "fa_hash kv=$kv nb=$nb ONCE0 $h0 ONCE$O $h1 $s"
  done; done
  [ $once_ok = 1 ] && log "CHECK PASS: ONCE=$O bit-identical to ONCE=0 on all fa_hash shapes, test-backend-ops all passed"
fi
[ $once_ok = 1 ] || { log "ONCE=$O gate failed: no timing arms"; exit 1; }
# ---------------------------------------------------------------- kperf
if on kperf; then
  filt='hsk=256,hsv=256,nh=4,nr23=\[6,1\],kv=(32768|98304|196608),nb=(1|5),'
  for o in 0 1 2 2 1 0; do
    tbo GGML_HIP_KVQ_ONCE=$o $N/bin/test-backend-ops perf -o FLASH_ATTN_EXT -b ROCm0 -p "$filt" 2>&1 | grep -E 'FLASH_ATTN_EXT\(' \
      | sed -E 's/.*kv=([0-9]+),nb=([0-9]+),.* ([0-9.]+) us\/run.*/\1 \2 \3/' | sed "s/^/once=$o /" >> "$out/kperf.txt"
  done
  python3 - "$out/kperf.txt" <<'PY' | tee -a "$out/summary.txt"
import sys, statistics as st
from collections import defaultdict
d = defaultdict(list)
for l in open(sys.argv[1]):
    o, kv, nb, us = l.split(); d[(o, int(kv), int(nb))].append(float(us))
for kv, nb in sorted({k[1:] for k in d}):
    b = st.mean(d[("once=0", kv, nb)])
    kvb = kv * 4 * 144 * 2  # q4_0 K + V bytes, 4 KV heads, D 256
    row = "  ".join(f"{o} {st.mean(d[(o, kv, nb)]):7.1f} us {100*(st.mean(d[(o, kv, nb)])/b-1):+5.1f}% {kvb/st.mean(d[(o, kv, nb)])/1e3:4.0f} GB/s"
                    for o in ("once=0", "once=1", "once=2") if (o, kv, nb) in d)
    print(f"kperf kv={kv:>6} nb={nb}: {row}")
PY
fi
# ---------------------------------------------------------------- pmc: DRAM read bytes per kvq dispatch
if on pmc; then
  /opt/rocm/core-10.0/bin/rocprofv3-avail list --pmc > "$out/pmc-avail.txt" 2>&1 || /opt/rocm/core-10.0/bin/rocprofv3 -L > "$out/pmc-avail.txt" 2>&1
  ctr=""; for c in FETCH_SIZE GL2C_EA_RDREQ_64B GL2C_EA_RDREQ_32B TCC_EA0_RDREQ_64B TCC_EA_RDREQ; do
    grep -qw "$c" "$out/pmc-avail.txt" && { ctr=$c; break; }; done
  log "pmc counter: ${ctr:-none found (see pmc-avail.txt)}"
  if [ -n "$ctr" ]; then
    for c in "98304 5" "196608 5" "196608 1"; do set -- $c; for o in 0 1 2; do
      d=$out/pmc-$1-$2-$o; rm -rf $d
      ( export GGML_HIP_PM4=0 GGML_HIP_KVQ_ONCE=$o; LD_LIBRARY_PATH=$N/bin:/opt/rocm/core-10.0/lib taskset -c 2-5 \
        /opt/rocm/core-10.0/bin/rocprofv3 --pmc $ctr --output-format csv -d $d -o p -- \
        $N/bin/test-backend-ops perf -o FLASH_ATTN_EXT -b ROCm0 -p "hsk=256,hsv=256,nh=4,nr23=\[6,1\],kv=$1,nb=$2," ) > $d.log 2>&1
      f=$(find $d -name '*counter_collection.csv' | head -1)
      python3 - "$f" "$ctr" "$1" "$2" "$o" <<'PY' | tee -a "$out/summary.txt"
import csv, sys
f, ctr, kv, nb, o = sys.argv[1:]
v = [float(r["Counter_Value"]) for r in csv.DictReader(open(f)) if "flash_attn_ext_kvq" in r["Kernel_Name"]] if f else []
kvb = int(kv) * 4 * 144 * 2
scale = 1024 if ctr == "FETCH_SIZE" else (64 if "64B" in ctr else 32 if "32B" in ctr else 64)  # FETCH_SIZE is in KB
if v:
    per = sum(v) / len(v) * scale
    print(f"pmc {ctr} kv={kv} nb={nb} once={o}: {per/1e6:.1f} MB per kvq dispatch ({len(v)} dispatches) = {per/kvb:.2f}x the q4_0 K+V bytes")
else:
    print(f"pmc kv={kv} nb={nb} once={o}: no kvq records")
PY
    done; done
  fi
fi
# ---------------------------------------------------------------- md5 + spec_sweep
if on md5; then
  i=0
  # md5 "fresh" = the first request of a new server; "after" = after spec_sweep (the prompt cache then serves the chat
  # template prefix, a different batch split -> its own md5; run 1 showed N0 fresh 09c9d3c1 vs P/N1 after-sweep c23506c7)
  for arm in P N2 N2 P N0; do
    case $arm in P) b=$P; e=(X=0) ;; N2) b=$N; e=(GGML_HIP_KVQ_ONCE=$O) ;; N0) b=$N; e=(GGML_HIP_KVQ_ONCE=0) ;; esac
    i=$((i + 1)); lab=md5-$arm-$i; srv $lab $b "${e[@]}" || continue
    log "md5 fresh $arm $(greedy_md5)"
    [ $arm = N0 ] && { stop_port $port; continue; }
    r=$(cd ~/qwen-opt && taskset -c 2-5 $py spec_sweep.py --label "kvq2-$lab" --port $port --temps 1.0 --seeds 1,2,3 | tail -1)
    echo "spec $arm $r" >> "$out/sweep.txt"; log "spec_sweep $arm: $r"
    log "md5 after-sweep $arm $(greedy_md5) (run 1: c23506c7)"
    stop_port $port
  done
fi
# ---------------------------------------------------------------- long context ABBA
if on long; then
  i=0
  for arm in N0 N2 N2 N0; do
    i=$((i + 1)); lab=long-$arm-$i; o=0; [ $arm = N2 ] && o=$O
    srv $lab $N GGML_HIP_KVQ_ONCE=$o || continue
    taskset -c 2-5 $py $here/lc.py --port $port --label $lab --out "$out/lc.jsonl" --depths ${LONG_DEPTHS:-199000} | tee -a "$out/long.txt"
    stop_port $port
  done
  python3 - "$out/lc.jsonl" <<'PY' | tee -a "$out/summary.txt"
import json, sys, statistics as st
from collections import defaultdict
d = defaultdict(list)
for l in open(sys.argv[1]):
    r = json.loads(l); d[(r["label"].split("-")[1], r["depth"])].append(r)
for depth in sorted({k[1] for k in d}):
    a, b = d.get(("N0", depth), []), d.get(("N2", depth), [])
    if not a or not b: continue
    ta, tb = st.mean(r["decode_tps"] for r in a), st.mean(r["decode_tps"] for r in b)
    ma, mb = st.mean(r["ms_step"] for r in a), st.mean(r["ms_step"] for r in b)
    md5 = {r["md5"] for r in a + b}
    print(f"long {depth:>6}: decode {ta:.2f} -> {tb:.2f} t/s ({100*(tb/ta-1):+.2f}%), {ma:.2f} -> {mb:.2f} ms/step, "
          f"md5 {'IDENTICAL ' + md5.pop() if len(md5) == 1 else 'DIFFERENT ' + ','.join(sorted(md5))}")
PY
fi
log "done $(date -u +%FT%TZ); results $out"
