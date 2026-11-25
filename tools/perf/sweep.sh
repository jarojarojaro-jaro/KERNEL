#!/usr/bin/env bash
# Fast variant sweep on ONE resident llama-server (runtime switch file, no model reload): for each variant
# (space-separated NAME=VAL,NAME=VAL; "base" = no switches) run R rounds of a short decode probe (T=0 160 tok,
# T=0.7 200 tok, seed 1) interleaved with the base; prints t/s per variant and seconds per variant. Runs ON the box.
# usage: sweep.sh PROFILE BUILD_BIN "VAR1" "VAR2" ...   (env R=2)
set -uo pipefail
P=$1 B=$2; shift 2; D=$(cd "$(dirname "$0")" && pwd); source $D/profiles/$P.env
SW=/tmp/sweep-switch.$$; : > $SW; PORT=18796; R=${R:-2}
~/qwen-opt/l1tok/chat8080.sh stop
env $RUN_ENV GGML_HIP_RUNTIME_SWITCH_FILE=$SW LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib taskset -c 2-5 $B/llama-server -m $MODEL $SRV_ARGS $SPEC_ARGS --port $PORT > /tmp/sweep-srv.log 2>&1 & SP=$!
trap 'kill -TERM $SP; sleep 3; kill -9 $SP 2>/dev/null; rm -f $SW' EXIT
t0=$(date +%s); for _ in $(seq 400); do curl -sf 127.0.0.1:$PORT/health >/dev/null && break; sleep 1; done; echo "server ready in $(( $(date +%s) - t0 )) s"
probe() { python3 - $PORT <<'PY'
import json,sys,urllib.request
port=sys.argv[1]; out=[]
for temp,n,p in ((0.0,160,"Write a Python function that merges two sorted lists, with a docstring and three tests."),(0.7,200,"Tell me a short story about a lighthouse keeper.")):
    b={"messages":[{"role":"user","content":p}],"max_tokens":n,"temperature":temp,"seed":1,"cache_prompt":False,"chat_template_kwargs":{"enable_thinking":False}}
    r=json.load(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",data=json.dumps(b).encode(),headers={"Content-Type":"application/json"}),timeout=300))
    out.append(r["timings"]["predicted_per_second"])
print(f"{out[0]:.1f} {out[1]:.1f}")
PY
}
set_var() { if [ "$1" = base ]; then : > $SW; else echo "$1" | tr ',' '\n' > $SW; fi; sleep 0.3; }
probe > /dev/null   # warm-up
for v in "$@"; do
  s=$(date +%s.%N); A=(); V=()
  for r in $(seq $R); do set_var base; A+=("$(probe)"); set_var "$v"; V+=("$(probe)"); done
  python3 - "$v" "${A[*]}" "${V[*]}" "$s" <<'PY'
import sys,time,statistics as st
v,a,b,s=sys.argv[1],list(map(float,sys.argv[2].split())),list(map(float,sys.argv[3].split())),float(sys.argv[4])
a0,a7,b0,b7=a[0::2],a[1::2],b[0::2],b[1::2]
f=lambda x,y:(st.median(y)/st.median(x)-1)*100
print(f"SWEEP {v}: T=0 {st.median(a0):.1f} -> {st.median(b0):.1f} ({f(a0,b0):+.1f}%)  T=0.7 {st.median(a7):.1f} -> {st.median(b7):.1f} ({f(a7,b7):+.1f}%)  [{time.time()-s:.0f} s]")
PY
done
echo "gfxhub $(journalctl -k --since '-30min' --no-pager | grep -c gfxhub)"
