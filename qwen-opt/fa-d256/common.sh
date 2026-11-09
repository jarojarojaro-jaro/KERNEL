#!/usr/bin/env bash
# Shared settings of the fa-d256 GPU jobs (report 68a #1: PR #31746 port + lossless FA D=256 prompt-kernel variants).
D=$HOME/qwen-opt/fa-d256
BIN=$HOME/wt/fa-d256/build-hip/bin
PROD=$HOME/llama-topka/bin
M=$HOME/models/orca/Qwen3.8-27B-Uncensored-Q4_K_M.gguf
# every compiled GGML_HIP_FA_D256_VAR mask (fattn-mma-f16.cuh GGML_CUDA_FATTN_MMA_D256_VARIANTS) + 0
VARS_ALL="0 1 2 3 7 11 15 16 19 23 35 51 67 83 131 147"
# bit-identical by construction (no 4/8 bit)
VARS_LOSSLESS="1 2 3 16 19 35 51 67 83 131 147"
export GGML_HIP_PM4=0
