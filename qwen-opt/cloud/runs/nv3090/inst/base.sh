#!/usr/bin/env bash
# ON the instance: baseline ABBA U0 U1 T | T U1 U0 on Qwen3.8-27B UD-Q6_K_M, ctx 32768, KV q4_0 (nv-3090, 2026-10-20).
# p1: chat T=1 seeds 1,2,3 + chat T=0 + mvs + short (+ near-max-ctx fill for U1/T); p2: chat T=1 seeds 4,5,6 + mvs.
set -uo pipefail
cd /root/cloud
export MODEL=Qwen3.8-27B-UD-Q6_K_M.gguf CTX=32768 CPUS=0-5 OUT=/root/results/nv3090/logs
SEEDS=1,2,3 ./arm.sh base.U0.p1 U0 chat1,chat0,mvs,short
SEEDS=1,2,3 ./arm.sh base.U1.p1 U1 chat1,chat0,mvs,short,long
SEEDS=1,2,3 ./arm.sh base.T.p1  T  chat1,chat0,mvs,short,long
SEEDS=4,5,6 ./arm.sh base.T.p2  T  chat1,mvs
SEEDS=4,5,6 ./arm.sh base.U1.p2 U1 chat1,mvs
SEEDS=4,5,6 ./arm.sh base.U0.p2 U0 chat1,mvs
touch $OUT/base.done
