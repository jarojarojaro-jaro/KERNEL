#!/usr/bin/env bash
# Nib (Chromadera, 2e16cf0) vs our Maya production on the same xbench harness (Q1-Q5 T=0, Q6 T=0.7, L2048, L8192), XTX.
# usage: nib-ab.sh nib-q8|nib-q4|nib-q8-dense|maya
# Nib: NVFP4-Mixed pack (not uncensored), DSpark MTP, ctx 262848, slots 1, no vision; maya: production maya-atomic.json
set -uo pipefail
arm=$1; PORT=18796; out=$HOME/qwen-opt/nib/out; mkdir -p $out; export GGML_HIP_PM4=0
N=$HOME/wt/nib/build/nib; M=$HOME/models/nib
~/qwen-opt/l1tok/chat8080.sh stop
# 2026-11-25: an orphan test server on the port answered a whole A/B (k165): the queue is serial, so anything here is ours and stale
pkill -9 -f "port $PORT"; sleep 2; ss -ltn | grep -q ":$PORT " && { echo "port $PORT busy"; exit 4; }
case $arm in
  nib-q8-dense*) a=(--kv-type q8_0 --sparse-pages 0);;
  nib-q8*)       a=(--kv-type q8_0 --sparse-pages 224);;
  nib-q4*)       a=(--kv-type q4_0 --sparse-pages 224);;
esac
if [[ $arm == maya* ]]; then
  cd ~/k134/maya/src && LD_LIBRARY_PATH=/opt/rocm/core-10.0/lib taskset -c 2-5 ~/qwen-opt/mtp-train/.venv/bin/python serve/server.py --engine maya \
    --config ${MAYA_CFG:-/home/jaro/k134/maya-atomic.json} --port $PORT --host 127.0.0.1 > $out/$arm.log 2>&1 & srv=$!
else
  cd $M && HIP_VISIBLE_DEVICES=0 taskset -c 2-5 $N serve -m $M/Inkling-2-Mini-NVFP4-Mixed.gguf --host 127.0.0.1 --port $PORT --slots 1 \
    -c 262848 "${a[@]}" --mtp $M/mtp.safetensors --no-vision > $out/$arm.log 2>&1 & srv=$!
fi
cleanup() { kill -TERM $srv 2>/dev/null; for _ in $(seq 30); do kill -0 $srv 2>/dev/null || break; sleep 1; done; kill -9 $srv 2>/dev/null; pkill -9 -f 'serve/server.py --engine maya' 2>/dev/null; pkill -9 -f 'maya-ik2.adq4k' 2>/dev/null; pkill -9 -f 'nib serve' 2>/dev/null; pkill -9 -f "port $PORT"; true; }
trap cleanup EXIT
for _ in $(seq 400); do curl -sf 127.0.0.1:$PORT/health >/dev/null && break; kill -0 $srv 2>/dev/null || { echo "$arm exited"; tail -15 $out/$arm.log; exit 1; }; sleep 1; done
sleep 3
taskset -c 2-5 timeout 600 python3 ~/qwen-opt/nib/wall.py $PORT "$arm" | tee -a $out/nib.txt
rocm-smi --showmeminfo vram 2>/dev/null | grep -i "used" | head -1
echo "gfxhub $(journalctl -k --since "-15min" --no-pager | grep -c gfxhub)"
