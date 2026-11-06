#!/bin/bash
# bugcheck.sh: ~5 min reproduction test of the kernel-6.8 OD mask bug ON OUR CARD (report 64 §3.2, §11 step 1),
# run ONCE after INSTALL.sh and before sweep.sh. Run it through the GPU queue (one job, own port, not :8080):
#   echo "eco-bugcheck|900|~/qwen-opt|bash ~/qwen-opt/thermal/bugcheck.sh" > /tmp/bc.jobs; ~/qwen-opt/queue/run-jobs.sh /tmp/bc.jobs
# It proves, physically (pwm1/RPM/median sclk, not sysfs text), that with the new xtx-eco + xtx-fan:
#   A) a cap commit under steady load does NOT drop the 100 % fan curve          (2200, then 2000 MHz)
#   B) the timer's own commits (load -> idle -> load) do NOT drop the clock cap   (cap 2200 through a 30 s idle gap)
#   C) `xtx-eco stock` really removes the cap (median sclk back above 2300 MHz)
# Any failure, amdgpu kernel message or hotspot >= 90 / VRAM >= 85 C -> stock, server stopped (one SIGTERM), FAIL.
# Result: ~/qwen-opt/thermal/bugcheck.PASS (required by sweep.sh) or bugcheck.FAIL, details in thermal/bugcheck-<time>/.
set -u
cd ~/qwen-opt || exit 2
port=${PORT:-8094}
out=~/qwen-opt/thermal/bugcheck-$(date -u +%Y%m%dT%H%M); mkdir -p "$out"
since=$(date '+%Y-%m-%d %H:%M:%S')
eco() { sudo -n /usr/local/sbin/xtx-eco "$@"; }
fault_re='amdgpu.*(page fault|ring .* timeout|GPU reset begin|MES failed|MES might be|Failed to upload overdrive)'
hw=$(echo /sys/class/drm/card0/device/hwmon/hwmon*)
rm -f ~/qwen-opt/thermal/bugcheck.PASS ~/qwen-opt/thermal/bugcheck.FAIL

eco status > /dev/null || { echo "xtx-eco not installed / no sudo rule (run INSTALL.sh)" >&2; exit 2; }
systemctl cat xtx-fan.service 2>/dev/null | grep -q '^ExecStart=/usr/local/sbin/xtx-fan ' \
    || { echo "xtx-fan.service does not run /usr/local/sbin/xtx-fan (run INSTALL.sh)" >&2; exit 2; }
journalctl -k -b 0 --no-pager -o cat | grep -qE "$fault_re" && { echo "amdgpu fault/reset in this boot: no test" >&2; exit 2; }

guard=""; tl=""; load_pid=""
pgrep -f 'tools/gpu-guard.sh' > /dev/null || { ~/qwen-opt/tools/gpu-guard.sh > "$out/guard.out" 2>&1 & guard=$!; }
load_on() { ( while :; do .venv/bin/python spec_sweep.py --label bugcheck --port $port --temps 1.0 --seeds 3 > /dev/null 2>&1; done ) & load_pid=$!; }
load_off() { [ -n "$load_pid" ] && { kill "$load_pid" 2>/dev/null; pkill -P "$load_pid" 2>/dev/null; wait "$load_pid" 2>/dev/null; }; load_pid=""
             for _ in $(seq 60); do curl -s -m 2 "127.0.0.1:$port/slots" | grep -q '"is_processing":true' || break; sleep 1; done; }
stop_server() {
  local p; p=$(pgrep -f "llama-server.*--port $port( |$)") || return 0
  for _ in $(seq 60); do curl -s -m 2 "127.0.0.1:$port/slots" | grep -q '"is_processing":true' || break; sleep 1; done
  kill -TERM $p  # exactly ONE SIGTERM (report 55)
  for _ in $(seq 45); do kill -0 $p 2>/dev/null || return 0; sleep 1; done
  kill -KILL $p
}
cleanup() { load_off; eco stock > "$out/stock-end.txt" 2>&1; stop_server; [ -n "$tl" ] && kill $tl 2>/dev/null; [ -n "$guard" ] && kill $guard 2>/dev/null; }
trap cleanup EXIT
fail() { echo "FAIL: $*" | tee -a "$out/result.txt" >&2; cp "$out/result.txt" ~/qwen-opt/thermal/bugcheck.FAIL; exit 3; }
check() {
  local hot mem
  journalctl -k --since "$since" --no-pager -o cat 2>/dev/null | grep -E "$fault_re" > "$out/kernel-fault.txt" && fail "kernel: $(head -c 200 "$out/kernel-fault.txt")"
  hot=$(( $(cat $hw/temp2_input) / 1000 )); mem=$(( $(cat $hw/temp3_input) / 1000 ))
  [ "$hot" -ge 90 ] && fail "hotspot $hot C"; [ "$mem" -ge 85 ] && fail "VRAM $mem C"; return 0
}
apply() {   # apply LABEL ARGS...: xtx-eco sclk N / stock, must exit 0
  local lab=$1 rc; shift
  eco "$@" > "$out/$lab-apply.txt" 2>&1; rc=$?
  echo "$lab: xtx-eco $* rc=$rc" | tee -a "$out/result.txt"
  [ $rc = 0 ] || fail "$lab: xtx-eco $* rc=$rc"
  grep -q 'verify failed' "$out/$lab-apply.txt" && fail "$lab: needed a repair upload (fix did not hold)"
  check
}
vstep() {   # vstep LABEL: physical check under load; sets MED (median sclk); a repair upload counts as failure
  local lab=$1 rc; MED=""
  eco verify > "$out/$lab-verify.txt" 2>&1; rc=$?
  MED=$(sed -n 's/^verify: .*median sclk \([0-9]*\).*/\1/p' "$out/$lab-verify.txt" | head -1)
  echo "$lab: $(grep '^verify:' "$out/$lab-verify.txt" | head -1) rc=$rc" | tee -a "$out/result.txt"
  [ $rc = 0 ] || fail "$lab: verify rc=$rc"
  grep -q 'verify failed' "$out/$lab-verify.txt" && fail "$lab: needed a repair upload (fix did not hold)"
  [ -n "$MED" ] || fail "$lab: no median"
  check
}

eco stock > "$out/stock-start.txt" 2>&1 || fail "stock at start"
./thermal/tlog.sh "$out/telemetry.csv" & tl=$!
PORT=$port LOG=$out/server.log ./run-topka.sh qwen > "$out/server.out" 2>&1 & srv=$!
until curl -sf "127.0.0.1:$port/health" > /dev/null; do kill -0 $srv 2>/dev/null || fail "server failed"; sleep 1; done

load_on; sleep 20
vstep 0-stock; m_stock=$MED
[ "$m_stock" -ge 2300 ] || fail "stock median sclk $m_stock < 2300: card not power-bound, the cap test would not discriminate"

apply 1-A sclk 2200; sleep 10             # A: cap commit under steady load, fan must stay at 100 %
vstep 1-A; m_a=$MED
[ "$m_a" -le 2250 ] || fail "A: cap 2200 not effective (median $m_a)"

# B: idle gap -> xtx-fan commits the idle curve, then the load curve; both commits must keep the cap
t_b=$(date '+%Y-%m-%d %H:%M:%S')
load_off; sleep 30; check
grep -q '^1: 2200Mhz' < <(sed -n '/^OD_SCLK:/,/^OD_MCLK:/p' /sys/class/drm/card0/device/pp_od_clk_voltage) || fail "B: OD_SCLK readback lost 2200 during idle"
load_on; sleep 20
journalctl -t xtx-fan --since "$t_b" --no-pager -o cat > "$out/fan-commits-B.txt" 2>/dev/null
grep -q 'fan curve: idle.*sclk cap 2200' "$out/fan-commits-B.txt" && grep -q 'fan curve: load.*sclk cap 2200' "$out/fan-commits-B.txt" \
    || fail "B: xtx-fan did not commit idle+load with cap 2200 during the gap (see fan-commits-B.txt): inconclusive"
vstep 2-B; m_b=$MED
[ "$m_b" -le 2250 ] || fail "B: cap 2200 dropped by the timer commit (median $m_b)"

apply 3-A2 sclk 2000; sleep 10            # A again with a second cap change
vstep 3-A2; m_a2=$MED
[ "$m_a2" -le 2050 ] || fail "A2: cap 2000 not effective (median $m_a2)"

apply 4-C stock; sleep 10                 # C: stock really removes the cap
vstep 4-C; m_c=$MED
[ "$m_c" -ge 2300 ] || fail "C: stock did not remove the cap (median $m_c)"

load_off
echo "PASS: stock $m_stock, cap2200 $m_a, after timer $m_b, cap2000 $m_a2, stock again $m_c MHz (median sclk)" | tee -a "$out/result.txt"
cp "$out/result.txt" ~/qwen-opt/thermal/bugcheck.PASS
