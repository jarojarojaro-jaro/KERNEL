#!/usr/bin/env bash
# Ternary Bonsai 2.5 27B Uncensored (AtomicChat) on XTX, best measured 2026-11-25: prism fork 910442b (+2 HIP defines),
# Q2_0 lossless repack of AtomicChat's PTQ1_0 + prism MTP head, MTP n2, KV q4_0 (draft too). T=0.7 77.7 t/s, T=0 117.9,
# L2k 97.5, L8k 92.6, prefill ~730-790 t/s. Port 18796 (never 8080); holds /tmp/gpu.lock while serving (stops :8080,
# restores it on exit). Stop: touch ~/qwen-opt/bonsai25/STOP
exec 8>>/tmp/gpu.lock; flock 8
rm -f ~/qwen-opt/bonsai25/STOP
B=$HOME/wt/prism/build-hip/bin; export GGML_HIP_PM4=0 LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib
restore() { kill -TERM $SPID 2>/dev/null; sleep 5; kill -KILL $SPID 2>/dev/null; kill $GPID 2>/dev/null; ~/qwen-opt/l1tok/chat8080.sh restore 8>&-; }
trap restore EXIT
~/qwen-opt/l1tok/chat8080.sh stop 8>&-
~/qwen-opt/tools/gpu-guard.sh > ~/qwen-opt/bonsai25/gpu-guard.out 2>&1 8>&- & GPID=$!
taskset -c 2-5 $B/llama-server -m $HOME/models/bonsai25/Ternary-Bonsai-2.5-27B-Uncensored-Q2_0-mtp.gguf -ngl 999 -fa on \
  -ctk q4_0 -ctv q4_0 -c ${CTX:-65536} -np 1 --jinja --host 0.0.0.0 --port 18796 \
  --spec-type draft-mtp --spec-draft-n-max 2 -ctkd q4_0 -ctvd q4_0 --temp 0.7 --min-p 0 \
  > ~/qwen-opt/bonsai25/serve.log 2>&1 8>&- & SPID=$!
for i in $(seq 4320); do [ -f ~/qwen-opt/bonsai25/STOP ] && break; kill -0 $SPID 2>/dev/null || break; sleep 10; done
