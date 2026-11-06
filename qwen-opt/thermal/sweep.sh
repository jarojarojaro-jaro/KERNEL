#!/bin/bash
# Thermal "eco" sweep (user approval 2026-11-05; safety rules: report 64 §10.3, §11): cap ONLY the max shader clock,
# live, on one production Qwen server (run-topka.sh qwen) on its own port. Memory clock, voltage, power cap (285 W)
# and fan curve (xtx-fan, 100 % under load) stay as they are, so temperatures are directly comparable.
# Every cap change goes through `xtx-eco` (one commit with fan curve + cap), then a PHYSICAL check under load after
# 30 s of soak and again at the end of the soak (median sclk <= cap + 50, pwm1 >= 240, >= 3200 RPM). Any failed check,
# any amdgpu fault/reset in the kernel log, or hotspot >= 90 / VRAM >= 85 C -> stock, server stopped, exit 3. No retries.
# Per arm: SOAK s of continuous spec_sweep load (thermal steady state), then measure:
#   decode: spec_sweep.py T=1 seeds 1,2 (t/s), prefill: one ~16k-token prompt (prompt t/s), greedy md5 (T=0, 256 tok),
#   telemetry over each window separately (decode W / prefill W, edge/junction/mem C, sclk, fan) -> J/token (decode).
# Run bugcheck.sh first (once, after INSTALL.sh). Usage (inside run-jobs.sh):
#   ARMS="stock 2400 2200 2000 1800 2000 2400 stock" SOAK=360 sweep.sh
set -u
cd ~/qwen-opt || exit 2
port=${PORT:-8093}; soak=${SOAK:-360}; arms=${ARMS:-"stock 2400 2200 2000 1800 2000 2400 stock"}
out=~/qwen-opt/thermal/run-$(date -u +%Y%m%dT%H%M); mkdir -p "$out"
since=$(date '+%Y-%m-%d %H:%M:%S')
eco() { sudo -n /usr/local/sbin/xtx-eco "$@"; }
fault_re='amdgpu.*(page fault|ring .* timeout|GPU reset begin|MES failed|MES might be|Failed to upload overdrive)'
hw=$(echo /sys/class/drm/card0/device/hwmon/hwmon*)

# --- preconditions -------------------------------------------------------------------------------------------------
eco status > /dev/null || { echo "xtx-eco not installed / no sudo rule (run INSTALL.sh)" >&2; exit 2; }
systemctl cat xtx-fan.service 2>/dev/null | grep -q '^ExecStart=/usr/local/sbin/xtx-fan ' \
    || { echo "xtx-fan.service does not run /usr/local/sbin/xtx-fan (run INSTALL.sh)" >&2; exit 2; }
[ -e ~/qwen-opt/thermal/bugcheck.PASS ] || { echo "bugcheck.sh has not passed on this card" >&2; exit 2; }
journalctl -k -b 0 --no-pager -o cat | grep -qE "$fault_re" && { echo "amdgpu fault/reset in this boot: no sweep" >&2; exit 2; }
guard=""; tl=""; soak_pid=""
pgrep -f 'tools/gpu-guard.sh' > /dev/null || { ~/qwen-opt/tools/gpu-guard.sh > "$out/guard.out" 2>&1 & guard=$!; }

stop_soak() { [ -n "$soak_pid" ] && { kill "$soak_pid" 2>/dev/null; pkill -P "$soak_pid" 2>/dev/null; wait "$soak_pid" 2>/dev/null; }; soak_pid=""; }
stop_server() {
  local p; p=$(pgrep -f "llama-server.*--port $port( |$)") || return 0
  for _ in $(seq 60); do curl -s -m 2 "127.0.0.1:$port/slots" | grep -q '"is_processing":true' || break; sleep 1; done
  kill -TERM $p  # exactly ONE SIGTERM (report 55)
  for _ in $(seq 45); do kill -0 $p 2>/dev/null || return 0; sleep 1; done
  kill -KILL $p
}
# order: load off, stock (safe direction, quick), then the server (waits for idle, one SIGTERM)
cleanup() { stop_soak; eco stock > "$out/stock-end.txt" 2>&1; stop_server; [ -n "$tl" ] && kill $tl 2>/dev/null; [ -n "$guard" ] && kill $guard 2>/dev/null; }
trap cleanup EXIT
abort() { echo "ABORT: $*" | tee -a "$out/ABORT.txt" >&2; exit 3; }
check_kernel() { if journalctl -k --since "$since" --no-pager -o cat 2>/dev/null | grep -E "$fault_re" > "$out/kernel-fault.txt"; then abort "kernel: $(head -c 200 "$out/kernel-fault.txt")"; fi; }
check_temps() {
  local hot mem; hot=$(( $(cat $hw/temp2_input) / 1000 )); mem=$(( $(cat $hw/temp3_input) / 1000 ))
  [ "$hot" -ge 90 ] && abort "hotspot $hot C"; [ "$mem" -ge 85 ] && abort "VRAM $mem C"; return 0
}
verify() {  # $1 = label; xtx-eco verify: 0 ok; anything else = abort (it has already gone to stock on 3)
  local rc; eco verify > "$out/verify-$1.txt" 2>&1; rc=$?
  echo "$1 verify rc=$rc: $(grep '^verify:' "$out/verify-$1.txt" | tail -1)" | tee -a "$out/verify.log"
  [ $rc = 0 ] || abort "verify $1 rc=$rc"
}

eco stock > "$out/stock-start.txt" 2>&1 || abort "stock at start failed"
./thermal/tlog.sh "$out/telemetry.csv" & tl=$!
PORT=$port LOG=$out/server.log ./run-topka.sh qwen > "$out/server.out" 2>&1 & srv=$!
until curl -sf "127.0.0.1:$port/health" > /dev/null; do kill -0 $srv 2>/dev/null || abort "server failed"; sleep 1; done
# ~16k-token prefill prompt from our own source tree (deterministic)
python3 - "$out/prefill.json" <<'EOF'
import json, sys, glob
txt = "".join(open(f, errors="ignore").read() for f in sorted(glob.glob("/home/jaro/qwen-opt/*.py"))[:40])[:60000]
json.dump({"prompt": "Summarize this code:\n" + txt, "n_predict": 1, "cache_prompt": False}, open(sys.argv[1], "w"))
EOF
# telemetry columns: time,gpu_w,cap_w,sclk,mclk,edge,junction,mem,fan_rpm,...
tel() { awk -F, -v a="$1" -v b="$2" 'NR>1 && $1>=a && $1<=b {n++; w+=$2; e+=$6; j+=$7; m+=$8; s+=$4; f+=$9} END{if(n) printf "%.0f,%.1f,%.1f,%.1f,%.0f,%.0f", w/n,e/n,j/n,m/n,s/n,f/n; else printf ",,,,,"}' "$out/telemetry.csv"; }
echo "arm,sclk_cap,decode_tps,prefill_tps,prefill_tokens,dec_w,edge_c,junction_c,mem_c,sclk_avg,fan_rpm,prefill_w,j_per_tok_decode,md5" > "$out/results.csv"
i=0
for arm in $arms; do
  i=$((i + 1)); lab="$i-$arm"
  if [ "$arm" = stock ]; then eco stock > "$out/set-$lab.txt" 2>&1 || abort "stock $lab rc=$?"
  else eco sclk "$arm" > "$out/set-$lab.txt" 2>&1; rc=$?; [ $rc = 0 ] || [ $rc = 4 ] || abort "sclk $arm rc=$rc"; fi
  t_end=$(( $(date +%s) + soak ))
  ( while [ "$(date +%s)" -lt "$t_end" ]; do .venv/bin/python spec_sweep.py --label soak --port $port --temps 1.0 --seeds 3 > /dev/null 2>&1; done ) &
  soak_pid=$!
  sleep 30; verify "$lab-early"; check_kernel; check_temps
  while [ $(( t_end - $(date +%s) )) -gt 60 ]; do sleep 10; check_kernel; check_temps; done
  verify "$lab-late"
  wait "$soak_pid" 2>/dev/null; soak_pid=""
  m0=$(date -u +%FT%T)
  dec=$(.venv/bin/python spec_sweep.py --label "eco-$arm" --port $port --temps 1.0 --seeds 1,2 2>&1 | tee -a "$out/spec_sweep.txt" | grep -oE 'median +[0-9.]+ t/s' | tail -1 | grep -oE '[0-9.]+')
  m1=$(date -u +%FT%T)
  pre=$(curl -s -m 300 "127.0.0.1:$port/completion" -H 'Content-Type: application/json' -d @"$out/prefill.json")
  pps=$(echo "$pre" | python3 -c 'import json,sys; t=json.load(sys.stdin)["timings"]; print(round(t["prompt_per_second"],1), t["prompt_n"])')
  m2=$(date -u +%FT%T)
  md5=$(curl -s -m 120 "127.0.0.1:$port/v1/chat/completions" -H 'Content-Type: application/json' \
        -d '{"messages":[{"role":"user","content":"Explain how a hash map works, step by step."}],"max_tokens":256,"temperature":0,"seed":1}' \
        | python3 -c 'import json,sys,hashlib; print(hashlib.md5(json.load(sys.stdin)["choices"][0]["message"]["content"].encode()).hexdigest()[:8])')
  check_kernel
  td=$(tel "$m0" "$m1"); tp=$(tel "$m1" "$m2")
  w=${td%%,*}; pw=${tp%%,*}; jpt=$(python3 -c "print(round($w/$dec,2) if '$dec' and '$w' else '')" 2>/dev/null)
  echo "$arm,$arm,$dec,${pps% *},${pps#* },$td,$pw,$jpt,$md5" | tee -a "$out/results.csv"
done
echo "done: $out"
