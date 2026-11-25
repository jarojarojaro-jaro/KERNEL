#!/usr/bin/env bash
# Nib --lora (AtomicChat Inkling-2-Mini-Uncensored) on the same harness as nib-ab.sh: wall.py (T=0 / T=0.7)
# + refusal.py (5 prompts, T=0).  Binary: ~/wt/nib-unc (patch ~/qwen-opt/nib/nib-uncensored.patch).
# usage: nib-unc-ab.sh unc-q4|unc-q8|stock-q4   (stock-q4 = the nib-unc binary WITHOUT --lora: must match nib-q4)
set -uo pipefail
arm=$1; PORT=18796; out=$HOME/qwen-opt/nib/out; mkdir -p $out; export GGML_HIP_PM4=0
N=$HOME/wt/nib-unc/build/nib; M=$HOME/models/nib; LORA=$HOME/models/inkling/Inkling-2-Mini-Uncensored-LoRA.gguf
~/qwen-opt/l1tok/chat8080.sh stop
# 2026-11-25: an orphan test server on the port answered a whole A/B (k165): the queue is serial, so anything here is ours and stale
pkill -9 -f "port $PORT"; sleep 2; ss -ltn | grep -q ":$PORT " && { echo "port $PORT busy"; exit 4; }
case $arm in
  unc-q8*)   a=(--kv-type q8_0 --sparse-pages 224 --lora $LORA);;
  unc-q4*)   a=(--kv-type q4_0 --sparse-pages 224 --lora $LORA);;
  stock-q4*) a=(--kv-type q4_0 --sparse-pages 224);;
  *) echo "unknown arm $arm"; exit 2;;
esac
cd $M && HIP_VISIBLE_DEVICES=0 taskset -c 2-5 $N serve -m $M/Inkling-2-Mini-NVFP4-Mixed.gguf --host 127.0.0.1 --port $PORT --slots 1 \
  -c 262848 "${a[@]}" --mtp $M/mtp.safetensors --no-vision > $out/$arm.log 2>&1 & srv=$!
cleanup() { kill -TERM $srv 2>/dev/null; for _ in $(seq 30); do kill -0 $srv 2>/dev/null || break; sleep 1; done; kill -9 $srv 2>/dev/null; pkill -9 -f 'nib serve' 2>/dev/null; pkill -9 -f "port $PORT"; true; }
trap cleanup EXIT
for _ in $(seq 400); do curl -sf 127.0.0.1:$PORT/health >/dev/null && break; kill -0 $srv 2>/dev/null || { echo "$arm exited"; tail -15 $out/$arm.log; exit 1; }; sleep 1; done
sleep 3
grep -m1 "^\[lora\]" $out/$arm.log
taskset -c 2-5 timeout 600 python3 ~/qwen-opt/nib/refusal.py $PORT "$arm" | tee -a $out/nib-unc.txt
taskset -c 2-5 timeout 600 python3 ~/qwen-opt/nib/wall.py $PORT "$arm" | tee -a $out/nib-unc.txt
rocm-smi --showmeminfo vram 2>/dev/null | grep -i "used" | head -1
echo "gfxhub $(journalctl -k --since "-15min" --no-pager | grep -c gfxhub)"
