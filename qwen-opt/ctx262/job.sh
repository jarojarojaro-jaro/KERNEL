#!/bin/bash
# ctx fit test: production chat config (run-topka.sh uncensored) at CTX, fill to FILL tokens, decode 256; peak VRAM.
set -u
ctx=$1; fill=$2; prof=${3:-uncensored}; port=18790; out=~/qwen-opt/ctx262/run-$prof-$ctx; mkdir -p $out
export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0; unset QUEUE_PM4_SAFETY
( while :; do echo "$(date +%T) $(cat /sys/class/drm/card0/device/mem_info_vram_used)"; sleep 1; done ) > $out/vram.log & vm=$!
CTX=$ctx PORT=$port LOG=$out/server.log ~/qwen-opt/run-topka.sh $prof > $out/server.out 2>&1 & 
for i in $(seq 120); do curl -sf 127.0.0.1:$port/health >/dev/null && break; sleep 1; done
curl -sf 127.0.0.1:$port/health >/dev/null || { echo "LOAD FAIL"; tail -5 $out/server.out; kill $vm; exit 1; }
echo "loaded: VRAM $(( $(cat /sys/class/drm/card0/device/mem_info_vram_used)/1048576 )) MiB"
(cd ~/qwen-opt && .venv/bin/python spec_sweep.py --label "final-$prof-$ctx" --port $port --temps 1.0 --seeds 1,2,3 | tee $out/spec_sweep.txt)
python3 ~/qwen-opt/ctx262/fill.py $port $fill; rc=$?
echo "peak VRAM $(awk '{if($2>m)m=$2} END{print int(m/1048576)}' $out/vram.log) MiB of $(( $(cat /sys/class/drm/card0/device/mem_info_vram_total)/1048576 ))"
grep -iE "out of memory|failed to allocate|error" $out/server.log | head -3
p=$(pgrep -f "llama-server.*--port $port( |$)"); kill -TERM $p; for i in $(seq 60); do kill -0 $p 2>/dev/null || break; sleep 1; done; kill -0 $p 2>/dev/null && kill -KILL $p
kill $vm; exit $rc
