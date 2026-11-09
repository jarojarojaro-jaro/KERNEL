#!/usr/bin/env bash
# Step 7: one arm of the production pair (A = VAR 0, B = BEST, the fa-d256 binary): run-topka.sh uncensored at
# CTX 262144 (production config: MTP, lookup, PM4 WA=2 + GUARD, GPU verify, KV q4_0, ub 512, eco), then
# long 32k greedy md5 (T=0) -> spec_sweep T=1 seeds 1-3 -> 255k fill + 256 decode (ctx262 protocol, frozen corpus).
# Stop: ONE SIGTERM after idle, SIGKILL only after 60 s. usage: arm.sh LABEL VAR
set -uo pipefail
. "$HOME/qwen-opt/fa-d256/common.sh"
label=$1; var=$2
[ -f "$D/res/BEST" ] || { echo "no BEST: skipped"; exit 0; }
[ "$var" = BEST ] && var=$(cat "$D/res/BEST")
port=18790; out=$D/logs/$label; mkdir -p "$out"
export ROCM_DIR=${ARM_ROCM_DIR:-$HOME/wt/fa-d256/build-hip} CTX=262144 PORT=$port LOG=$out/server.log GGML_HIP_FA_D256_VAR=$var
export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0; unset QUEUE_PM4_SAFETY
grep -q '^1: 2200Mhz' < <(sed -n '/^OD_SCLK:/,/^OD_MCLK:/p' /sys/class/drm/card0/device/pp_od_clk_voltage) \
    && echo "eco: OD_SCLK 2200" || echo "WARNING: OD_SCLK is not 2200 (not touched by this job)"
( while :; do echo "$(date +%T) $(cat /sys/class/drm/card0/device/mem_info_vram_used)"; sleep 1; done ) > "$out/vram.log" & vm=$!
taskset -c 2-5 "$HOME/qwen-opt/run-topka.sh" uncensored > "$out/server.out" 2>&1 &
srv=$!
stop() { for _ in $(seq 60); do curl -s -m 2 "127.0.0.1:$port/slots" 2>/dev/null | grep -q '"is_processing":true' || break; sleep 1; done
         local p; p=$(pgrep -f "llama-server.*--port $port( |$)" | head -1)
         [ -n "$p" ] && kill -TERM "$p"
         for _ in $(seq 60); do pgrep -f "llama-server.*--port $port( |$)" >/dev/null || break; sleep 1; done
         pkill -9 -f "llama-server.*--port $port( |$)" && echo "$label: SIGKILL needed" || true
         wait $srv 2>/dev/null; kill $vm 2>/dev/null; }
trap stop EXIT
trap 'exit 1' TERM INT
for _ in $(seq 240); do curl -sf 127.0.0.1:$port/health >/dev/null && break; kill -0 $srv 2>/dev/null || break; sleep 1; done
curl -sf 127.0.0.1:$port/health >/dev/null || { echo "$label: LOAD FAIL"; tail -5 "$out/server.out"; exit 1; }
echo "$label: VAR=$var loaded, VRAM $(( $(cat /sys/class/drm/card0/device/mem_info_vram_used)/1048576 )) MiB, bin $(readlink -f /proc/$(pgrep -f "llama-server.*--port $port( |$)" | head -1)/exe)"
grep -m1 "GGML_HIP_FA_D256_VAR" "$out/server.log" "$out/server.out" 2>/dev/null
py=$HOME/qwen-opt/.venv/bin/python
taskset -c 2-5 "$py" "$D/long_md5.py" --port $port --label "$label" --out "$D/res/long_md5.txt"
(cd "$HOME/qwen-opt" && taskset -c 2-5 "$py" spec_sweep.py --label "fa-d256-$label" --port $port --temps 1.0 --seeds 1,2,3 | tee "$out/spec_sweep.txt")
taskset -c 2-5 python3 "$D/fill.py" $port 255000 | tee -a "$D/res/fill.txt"
echo "$label peak VRAM $(awk '{if($2>m)m=$2} END{print int(m/1048576)}' "$out/vram.log") MiB" | tee -a "$D/res/fill.txt"
grep -iE "out of memory|failed to allocate" "$out/server.log" | head -3
