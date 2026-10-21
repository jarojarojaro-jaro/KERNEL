#!/bin/bash
# report 53 checks (2)-(4): shortlist-on MTP md5 x2, GPU_VERIFY=0 with shortlist, near-tie gap at the first diff. GPU queue only.
set -uo pipefail
D=$HOME/qwen-opt/draft-shortlist; B=$HOME/wt/draft-shortlist/build-hip/bin; o=$D/md5
pkill -f 'llama-topka/bin/llama-server' && sleep 5
$HOME/qwen-opt/lookup/vram_ok.sh || exit 1
export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0 LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 \
    LLAMA_SPEC_COUPLED=1 LLAMA_SERVER_YIELD_FAST=2 GGML_HIP_PM4_MIN_DISPATCH=16 GGML_HIP_PM4_LAZY_EXEC=1 PORT=18873
SL="LLAMA_DRAFT_SHORTLIST=1 LLAMA_DRAFT_SHORTLIST_FACTORS=$D/best.bin LLAMA_DRAFT_SHORTLIST_K=$(cat $D/best.k)"
for r in r1 r2; do env $SL LLAMA_GPU_VERIFY=1 MODES=mtp taskset -c 2-5 $HOME/qwen-opt/fusion/greedy.sh $B $B $o/on-$r qwen > /dev/null; done
env $SL LLAMA_GPU_VERIFY=0 MODES=mtp taskset -c 2-5 $HOME/qwen-opt/fusion/greedy.sh $B $B $o/on-gv0 qwen > /dev/null
for f in $o/on-*.mtp.txt; do echo "${f##*/} $(md5sum < $f | cut -c1-8)"; done
grep -h "draft acceptance" $o/on-r1.mtp.log | head -2
export LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib
$B/llama-server --port 18874 --host 127.0.0.1 -np 1 --no-webui -m $HOME/models/Qwen3.8-27B-UD-Q4_K_XL.gguf -ngl 999 -fa on \
    -ctk q4_0 -ctv q4_0 -c 8192 > $o/gap.server.log 2>&1 &
pid=$!
for _ in $(seq 180); do curl -sf http://127.0.0.1:18874/health > /dev/null && break; sleep 1; done
$HOME/qwen-opt/.venv/bin/python $HOME/KERNEL/product/research/53-skrypty/nt_gap.py --port 18874 $o/qwen-a1.mtp.txt $o/qwen-a2.mtp.txt
$HOME/qwen-opt/.venv/bin/python $HOME/KERNEL/product/research/53-skrypty/nt_gap.py --port 18874 $o/qwen-a1.mtp.txt $o/on-r1.mtp.txt
kill $pid; for _ in $(seq 30); do kill -0 $pid 2>/dev/null || break; sleep 1; done; kill -9 $pid 2>/dev/null; wait $pid 2>/dev/null
exit 0
