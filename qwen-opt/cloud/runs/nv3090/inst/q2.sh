#!/usr/bin/env bash
# ON the instance: queue 2 (nv-3090, 2026-10-20): after queue 1, build comb (OCC+PIPE+Q8_WIDE), then quick gate +
# ABBA: Q8_WIDE, coupled sampling, draft depth 3 and 5 (config; A B C C B A).
set -uo pipefail
cd /root/cloud
while [ ! -f /root/results/nv3090/logs/q1.done ]; do sleep 10; done
./build.sh comb
./idea.sh q8w comb "" comb "GGML_CUDA_MMVQ_Q8_WIDE=1"
./idea.sh cpl comb "" comb "LLAMA_SPEC_COUPLED=1"
export MODEL=Qwen3.8-27B-UD-Q6_K_M.gguf CTX=32768 CPUS=0-5 OUT=/root/results/nv3090/logs
SEEDS=1,2 BIN=comb ./arm.sh dep.n4.p1 N chat1,chat0,mvs
SEEDS=1,2 BIN=comb ./arm.sh dep.n3.p1 N chat1,chat0,mvs DRAFT_N=3
SEEDS=1,2 BIN=comb ./arm.sh dep.n5.p1 N chat1,chat0,mvs DRAFT_N=5
SEEDS=3,4 BIN=comb ./arm.sh dep.n5.p2 N chat1,mvs DRAFT_N=5
SEEDS=3,4 BIN=comb ./arm.sh dep.n3.p2 N chat1,mvs DRAFT_N=3
SEEDS=3,4 BIN=comb ./arm.sh dep.n4.p2 N chat1,mvs
touch /root/results/nv3090/logs/q2.done
