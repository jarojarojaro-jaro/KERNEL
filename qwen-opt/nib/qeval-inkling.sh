#!/usr/bin/env bash
# HumanEval+ (164, greedy, thinking off, max 2048 tok.) on Inkling 2 Mini uncensored: Nib+LoRA (NVFP4) vs Maya prod (AD-Q4_K).
# usage: qeval-inkling.sh nib-unc|maya   (GPU, inside the queue); eval on CPU after: jakosc-mini.sh --tag qe-ARM --datasets humaneval eval/report
set -uo pipefail
arm=$1; PORT=18796; D=~/qwen-opt/evalplus; R=$D/runs/qe-$arm; mkdir -p $R; export GGML_HIP_PM4=0
~/qwen-opt/l1tok/chat8080.sh stop
pkill -9 -f "port $PORT"; sleep 2; ss -ltn | grep -q ":$PORT " && { echo "port $PORT busy"; exit 4; }
M=~/models/nib
case $arm in
  nib-unc) cd $M; HIP_VISIBLE_DEVICES=0 taskset -c 2-5 ~/wt/nib-unc/build/nib serve -m $M/Inkling-2-Mini-NVFP4-Mixed.gguf --host 127.0.0.1 --port $PORT --slots 1 \
             -c 262848 --kv-type q4_0 --sparse-pages 224 --lora ~/models/inkling/Inkling-2-Mini-Uncensored-LoRA.gguf --mtp $M/mtp.safetensors --no-vision > $R/server.log 2>&1 & srv=$! ;;
  maya) cd ~/k134/maya/src; LD_LIBRARY_PATH=/opt/rocm/core-10.0/lib taskset -c 2-5 ~/qwen-opt/mtp-train/.venv/bin/python serve/server.py --engine maya \
             --config /home/jaro/k134/maya-atomic.json --port $PORT --host 127.0.0.1 > $R/server.log 2>&1 & srv=$! ;;
  *) echo "unknown arm"; exit 2 ;;
esac
cleanup() { kill -TERM $srv 2>/dev/null; for _ in $(seq 30); do kill -0 $srv 2>/dev/null || break; sleep 1; done; kill -9 $srv 2>/dev/null; pkill -9 -f "port $PORT"; pkill -9 -f 'nib serve'; pkill -9 -f 'maya-ik2.adq4k'; true; }
trap cleanup EXIT
for _ in $(seq 400); do curl -sf 127.0.0.1:$PORT/health >/dev/null && break; kill -0 $srv 2>/dev/null || { echo "$arm exited"; tail -15 $R/server.log; exit 1; }; sleep 1; done
sleep 3; t0=$(date +%s)
GEN_NOTHINK=1 taskset -c 2-5 timeout 780 $D/.venv/bin/python $D/gen.py --dataset humaneval --base-url http://127.0.0.1:$PORT/v1 --model local --out $R/humaneval.jsonl --max-tokens 2048 2>&1 | grep -v "it/s\]$" | tail -3
echo "QEVAL $arm: $(wc -l < $R/humaneval.jsonl) samples in $(( $(date +%s) - t0 )) s"
echo "gfxhub $(journalctl -k --since '-15min' --no-pager | grep -c gfxhub)"
