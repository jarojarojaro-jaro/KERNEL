# LOO plan: 65 patches e60eff95f..c36fd2c87

- runtime env switch (verified in source): 27
- runtime CLI switch (OFF = drop the args): 2
- build-time only (git revert + rebuild): 22 (clean revert 8, conflicts 14; on the default path 21)
- non-speed: 14 (Vulkan backend only 5, correctness fix 2, build hygiene 1, opt-in 1, numerics fix 1, tests only 1, opt-in WIP 1, tooling 1, refactor 1)

## Patches

| # | sha | cat | OFF | models | measures | revert | note | subject |
|---|---|---|---|---|---|---|---|---|
| 01 | 95a0c83d6 | build |  | qwen | serve | CONFLICT mmvq.cu (later: 02,03,05,12,13,16,21,22,24,25,28,37,49,51,52,54,56,62,63,64) | multi-column MMVQ (MTP verify) | HIP mmvq: multi-column (2-8) vec_dot for RDNA3 with wide contiguous loads (Q4_K/Q5_K/Q6_K/ |
| 02 | 72cfa5656 | build |  | qwen | serve | CONFLICT mmvq.cu (later: 03,05,12,13,16,21,22,24,25,28,37,49,51,52,54,56,62,63,64) | multi-column MMVQ i-quants/Q2_K | HIP mmvq multi-column: i-quants, Q2_K, per-type rows per block on RDNA3 |
| 03 | 3a05006a0 | build |  | qwen,lfm | tg,serve | CONFLICT common.cuh,ggml-cuda.cu,mmvq.cu (later: 05,12,13,14,15,16,17,19,21,22,23,24,25,27,28,33,37,38,49,50,51,52,53,54,56,57,58,59,60,62,63,64) | q8_1 activation reuse | CUDA/HIP mmvq: reuse q8_1 activations across consecutive MUL_MATs with the same src1 |
| 04 | 3b15c2b6d | cli | drop --spec-draft-vocab --spec-draft-vocab-n | qwen | serve |  | reduced-vocabulary draft head; OFF = full-vocabulary draft head | MTP: optional reduced-vocabulary draft LM head (--spec-draft-vocab) |
| 05 | 8af9de8f8 | nonspeed |  |  |  |  | build hygiene (drops a local tuning include) | mmvq: drop local tuning include |
| 06 | 68e163cf4 | nonspeed |  |  |  |  | Vulkan backend only (not in the ROCm path) | vulkan: AMD RDNA small-M matvec uses float path with 256-thread workgroups (ssm_alpha/beta |
| 07 | afbb23886 | nonspeed |  |  |  |  | Vulkan backend only (not in the ROCm path) | vulkan: MMVQ fast path for Q4_K/Q5_K/Q6_K/IQ4_XS with hoisted per-thread chunk decoding |
| 08 | 81e5fb913 | nonspeed |  |  |  |  | Vulkan backend only (not in the ROCm path) | vulkan: AMD RDNA uses the integer-dot MMVQ path for Q6_K from four columns on |
| 09 | f6e5de112 | nonspeed |  |  |  |  | Vulkan backend only (not in the ROCm path) | vulkan: AMD RDNA uses the float matvec path for m < 4096 above four columns |
| 10 | 6c7801bf6 | nonspeed |  |  |  |  | Vulkan backend only (not in the ROCm path) | vulkan: RDNA3/4 MMVQ uses 2 rows per workgroup at eight columns |
| 11 | 40c9bacdc | build |  | qwen | tg,serve | CONFLICT fattn-kvq.cu,fattn-kvq.cuh,test-backend-ops.cpp (later: 12,13,14,17,19,20,24,27,33,34,37,38,42,44,51,53,54,55,56,57,58) | FA kvq kernel for q4_0 KV (Qwen KV q4_0) | HIP FA: RDNA3 kernel reading the q4_0 KV cache directly for small batches |
| 12 | 6da87d000 | build |  | qwen | serve | CONFLICT ggml-cuda.cu,mmvq.cu,test-backend-ops.cpp (later: 13,14,15,16,17,19,20,21,22,24,25,27,28,33,34,37,38,42,44,49,50,51,52,53,54,55,56,57,58,59,60,62,63,64) | bias/residual ADD epilogue, multi-column MMVQ | CUDA/HIP: bias/residual ADD epilogue for multi-column MMVQ |
| 13 | a180bea04 | build |  | qwen | tg,serve | CONFLICT gated_delta_net.cu,ggml-cuda.cu,mmvq.cu,mmvq.cuh,test-backend-ops.cpp (later: 14,15,16,17,19,20,21,22,24,25,27,28,33,34,35,37,38,42,44,45,49,50,51,52,53,54,55,56,57,58,59,60,62,63,64) | GDN prologue fusion | CUDA/HIP: fuse the GATED_DELTA_NET prologue (alpha/beta projections, q/k l2 norm, state ga |
| 14 | 92b14b8b2 | build |  | qwen,lfm | tg,serve | CONFLICT ggml-cuda.cu,ssm-conv.cu,ssm-conv.cuh,test-backend-ops.cpp (later: 15,17,19,20,24,27,28,33,34,37,38,42,44,49,50,51,53,54,55,56,57,58,59,60) | conv-state concat/snapshots folded into SSM_CONV | CUDA/HIP: fold the conv-state concat, snapshot copies and gather into SSM_CONV |
| 15 | b9db88004 | build |  | qwen,lfm | tg,serve | CONFLICT common.cuh,ggml-cuda.cu,norm.cu (later: 17,19,23,24,25,27,28,33,37,38,49,50,51,53,54,56,57,58,59,60) | q8_1 activations written by norm/GLU/unary*mul | CUDA/HIP: write the q8_1 MMVQ activations from the producing norm/GLU/unary*mul kernels |
| 16 | ca4cccedb | build |  | qwen | tg,serve | CONFLICT mmvq.cu (later: 21,22,24,25,28,37,49,51,52,54,56,62,63,64) | GDN alpha/beta MMVQ templated on token count | CUDA/HIP: GDN alpha/beta MMVQ templated on the token count |
| 17 | a7e951497 | build |  | qwen | tg,serve | CONFLICT rope.cu,qwen35.cpp (later: 19,20,24,39,41,57) | IMROPE fused into RMS_NORM+MUL+ROPE | CUDA/HIP + qwen35: fuse IMROPE/MROPE into RMS_NORM+MUL+ROPE, drop the attention gate copy |
| 18 | 919080dca | nonspeed |  |  |  |  | correctness fix (FA race, upstream cherry-pick) | CUDA/HIP: fix race in flash_attn_ext_f16_process_tile when nbatch_combine != DKQ/2 (cherry |
| 19 | b1f8c19ac | build |  | qwen,lfm | tg,serve | CONFLICT ggml-cuda.cu,rope.cu,rope.cuh (later: 24,27,28,33,37,38,49,50,51,53,54,56,57,58,59,60) | q/k Hadamard rotation folded into norm+rope | CUDA/HIP: fold the q/k Hadamard rotation of a rotated KV cache into RMS_NORM+MUL+ROPE |
| 20 | c90db29c6 | build |  | qwen | serve | CONFLICT speculative.cpp,llama-context.cpp,llama-context.h,llama-cparams.h,llama-ext.h,llama-graph.cpp,llama-graph.h,llama-kv-cache.cpp,llama-model.cpp,qwen35.cpp (later: 24,29,30,32,33,34,36,38,39,41,46,47) | MTP draft chain graph (no switch; p_min>0 is not equivalent) | speculative + qwen35: greedy MTP drafts as one unrolled draft-chain graph |
| 21 | 60ce2a71f | build |  | qwen | serve | CONFLICT mmvq.cu (later: 22,24,25,28,37,49,51,52,54,56,62,63,64) | multi-column MMVQ buffer loads/occupancy/DPP | HIP/RDNA3 multi-column MMVQ: buffer-resource loads, per-type occupancy, Q6_K pipelining, t |
| 22 | 9f83f1f81 | build |  | qwen | serve | clean | multi-column MMVQ GLC|DLC streaming | HIP/RDNA3 multi-column MMVQ: stream weight loads past the per-CU caches (GLC/DLC) |
| 23 | ba90baf3a | nonspeed |  |  |  |  | correctness fix (fp16 clamp of q8_1 d/sum) | CUDA/HIP: clamp the fp16 (d, sum) of every q8_1 block written to +-65504 |
| 24 | 15db6f979 | env | GGML_HIP_MMVQ_PAIR=0 | qwen | tg,serve |  |  | CUDA/HIP: MMVQ pair launch for two products of the same src1 (GGML_HIP_MMVQ_PAIR) |
| 25 | 813fa7c34 | env | GGML_HIP_NORM_FAST=0 | qwen,lfm | tg,serve |  |  | CUDA/HIP: unrolled rms_norm*mul(+q8_1) for 2048..8192-column rows, DPP reductions (GGML_HI |
| 26 | bc0da48dd | env | GGML_HIP_ARGMAX_FAST=0 | qwen | serve |  | GPU argmax: MTP greedy drafts | CUDA/HIP: argmax with 16 loads in flight and DPP exchanges (GGML_HIP_ARGMAX_FAST) |
| 27 | 006490a99 | env | GGML_HIP_NORM_GATE=0 | qwen | tg,serve |  |  | CUDA/HIP: GDN gated output norm silu(z) * (rms_norm(x) * w) + q8_1 in one launch (GGML_HIP |
| 28 | 849b69978 | env | GGML_HIP_GDN_CONV_AB=0 | qwen | tg,serve |  |  | CUDA/HIP: GDN fused SSM_CONV and alpha/beta projections in one grid (GGML_HIP_GDN_CONV_AB) |
| 29 | 2eb088419 | env | LLAMA_ASYNC_INPUTS=0 | qwen,lfm | tg,serve |  |  | ggml-backend/llama: asynchronous graph input uploads (LLAMA_ASYNC_INPUTS) |
| 30 | 56be15abf | env | LLAMA_MTP_CHAIN_SCHED=0 | qwen | serve |  |  | llama: MTP draft chain on its own scheduler (LLAMA_MTP_CHAIN_SCHED) |
| 31 | 35d04b446 | env | LLAMA_SAMPLER_FAST_TOPK=0 LLAMA_SPEC_LAZY_SAVE=0 | qwen,lfm | serve |  | host sampler / server spec loop | common/server: top-k candidates without the full candidate array, no sampler copy per spec |
| 32 | 343c2fbbb | cli | drop --spec-draft-head-type --spec-mtp-type | qwen | serve |  | re-quantized MTP head/block; OFF = GGUF types (draft numerics differ, output identical) | llama/common: re-quantize the MTP draft head and MTP block at load time (--spec-draft-head |
| 33 | 3f8c8ddff | env | LLAMA_GDN_REPLAY=0 | qwen | serve |  | OFF also disables the later lag refinements 34-36, 38 [also introduces GGML_HIP_GDN_REPLAY] | ggml/llama: delta-net speculative rollback by replay of a lagged state (GATED_DELTA_NET_LA |
| 34 | 53be90b39 | build |  | qwen | serve | CONFLICT ggml.h,llama-graph.cpp,llama-graph.h,llama-memory-recurrent.cpp,llama-memory-recurrent.h (later: 36,38,39,41,46) | lag info layout (refines 33) | llama/ggml: GATED_DELTA_NET_LAG lag info as [n_seqs, 4], its first row is the state gather |
| 35 | bd2251523 | build |  | qwen | serve | clean | GDN_LAG load scheduling | CUDA/HIP: GATED_DELTA_NET_LAG issues the loads of the next pending row before the recurren |
| 36 | b1a203959 | build |  | qwen | serve | clean | lagged state read from its cache row (refines 33/34) | llama: the lagged delta-net state is read from its cache row (single cell), no gather inde |
| 37 | d3a0973ae | build |  | qwen | serve | clean | INACTIVE: verify batches of 9-16 columns: inactive at MTP n=4 (5 columns) | CUDA/HIP: RDNA3 verify batches of 9-16 columns: WMMA small-N MUL_MAT kernel, wide MMVQ dis |
| 38 | b9b476c87 | env | LLAMA_CONV_LAG=0 | qwen | serve |  |  | llama/CUDA: lagged conv history for the delta-net rollback by replay, no per-token conv sn |
| 39 | 7e9c73d8b | nonspeed |  |  |  |  | opt-in (--spec-draft-adaptive, not used by run-llm.sh); LLAMA_VERIFY_SCHED only with it [also introduces LLAMA_SPEC_DEPTH_POWER,LLAMA_VERIFY_SCHED] | common/llama: cost-priced adaptive MTP draft depth (--spec-draft-adaptive, opt-in), per-wi |
| 40 | 6aacfea49 | build |  | qwen,lfm | pp | clean | prefill: MMQ narrower tile | CUDA/HIP: RDNA3 MMQ picks a narrower tile when the widest one leaves CUs idle (48-row GDN  |
| 41 | 2b910b22f | build |  | qwen | serve,pp | clean | MTP layer K/V-only rows | llama: the qwen35 MTP layer computes only K/V for rows without output (prompt and verify r |
| 42 | cf397468e | build |  | qwen | pp | clean | prefill: FA MMA D=256 tile Q in SRAM | CUDA/HIP: RDNA FA MMA D=256 prompt tile keeps Q in SRAM (Q in registers spilled ~1.1 KB pe |
| 43 | 5a7562bee | nonspeed |  |  |  |  | numerics fix (bit-identical prompt logits of 42; KLD 0.0135 -> 0) | CUDA/HIP: FA MMA walks the K chunks in order unless K is the V view (MLA) |
| 44 | 01ab59798 | nonspeed |  |  |  |  | tests only | tests: perf cases for the Qwen3.5/3.8 27B prompt matmul shapes (FFN, GDN qkv, alpha/beta,  |
| 45 | 575e3d893 | build |  | qwen | pp | clean | prefill: GDN l2 pre-pass | CUDA/HIP: prompt batches of the fused-l2 GDN normalize q/k once per (head, token) in a pre |
| 46 | 0b5b15d17 | nonspeed |  |  |  |  | opt-in WIP (--spec-mtp-window, not used by run-llm.sh) | MTP: attention window of the MTP layer (--spec-mtp-window, WIP) |
| 47 | e84abb808 | env | LLAMA_KV_MASK_FAST=0 LLAMA_KV_SEQ_RM_SCAN=1 | qwen,lfm | serve |  | partial: the draft prompt-copy skip has no switch | llama/server: per-step host costs of the spec loop off the critical path |
| 48 | 41bb3da6a | env | LLAMA_SAMPLER_FAST_PENALTIES=0 | qwen,lfm | serve |  |  | common: fast top-k candidates also behind a penalties sampler that only lowers logits (LLA |
| 49 | 605fccd9a | env | GGML_HIP_Q8_IDS=0 | lfm | tg,serve |  |  | CUDA/HIP: the FFN norm writes the q8_1 activations of the single-token MoE gate/up MUL_MAT |
| 50 | be05dc19c | env | GGML_HIP_CONV_MUL=0 | lfm | tg,serve |  | OFF also disables 54/62 (they build on it) | CUDA/HIP: LFM2 shortconv: b*x and c*conv folded into the fused SSM_CONV, which writes the  |
| 51 | 862c02136 | env | GGML_HIP_MOE_DOWN_REDUCE=0 | lfm | tg,serve |  |  [also introduces GGML_HIP_Q8_IDS] | CUDA/HIP: single-token MoE tail (down MUL_MAT_ID, expert weighting, residual ADD) in one M |
| 52 | bcdf324d3 | env | GGML_HIP_MMVQ_N1_ROWS=1 | qwen,lfm | tg,serve |  | one-column K-quant MMVQ: Qwen plain decode + LFM | HIP/RDNA3 one-column MMVQ: 2 rows per block for the K-quants (GGML_HIP_MMVQ_N1_ROWS) |
| 53 | c15c84e83 | env | GGML_HIP_NORM_ROUTER=0 | lfm | tg,serve |  |  | CUDA/HIP: single-token MoE routing (FFN norm, F32 router, topk_moe) in one launch (GGML_HI |
| 54 | 5909da1f1 | env | GGML_HIP_INPROJ_CONV=0 | lfm | tg,serve |  |  | CUDA/HIP: LFM2 shortconv in_proj MMVQ with the fused conv as per-group ticket tails (GGML_ |
| 55 | 5f6c03fa9 | env | GGML_HIP_KVQ_Q8=0 | lfm | tg,serve |  | not bitwise (KLD-gated); KV q8_0 only | HIP/RDNA3 FA: the kvq decode kernel also reads a q8_0 KV cache (GGML_HIP_KVQ_Q8) |
| 56 | 04f10413e | env | GGML_HIP_GATE_UP_Q8=0 | lfm | tg,serve |  |  | CUDA/HIP: single-token gate/up(+GLU) MMVQ writes the q8_1 input of the down projection (GG |
| 57 | 7a963bc0c | env | GGML_HIP_ATTN_PREP=0 | lfm | tg,serve |  |  | CUDA/HIP: single-token attention input (q/k norm+rope+FWHT, v FWHT, q8_0 SET_ROWS of k and |
| 58 | 3a1279f95 | env | GGML_HIP_KVQ_FWHT=0 | qwen,lfm | tg,serve |  |  | CUDA/HIP: kvq attention applies the output FWHT (+ q8_1 for the o projection) in its combi |
| 59 | 9d493cf6e | env | GGML_HIP_INPUT_BATCH=0 | qwen,lfm | tg,serve |  |  | CUDA/HIP: batch the small async input uploads of a graph into one H2D copy + one scatter l |
| 60 | 1153adb69 | env | GGML_HIP_PM4=0 | qwen,lfm | tg,serve |  |  [also introduces GGML_HIP_PM4_DEBUG] | HIP/RDNA3: replay a captured decode graph as one PM4 indirect buffer on an own ROCr queue  |
| 61 | e5ca00ec4 | nonspeed |  |  |  |  | tooling (GGML_HIP_PM4_DEBUG=2 timing) [also introduces GGML_HIP_PM4_DEBUG] | HIP PM4 replay: GGML_HIP_PM4_DEBUG=2 per-launch timing (GPU timestamps of the tape, host s |
| 62 | 1b43bccae | env | GGML_HIP_CONV_ROWS4=0 | lfm | tg,serve |  |  | CUDA/HIP RDNA3: the shortconv in_proj MMVQ runs 4 rows per block (GGML_HIP_CONV_ROWS4) |
| 63 | 2cbcf771a | nonspeed |  |  |  |  | refactor (switches read through ggml_cuda_env_switch) [also introduces GGML_HIP_CONV_ROWS4,GGML_HIP_PM4] | CUDA/HIP: GGML_HIP_PM4 and GGML_HIP_CONV_ROWS4 read through ggml_cuda_env_switch (the fork |
| 64 | e41c2330e | env | GGML_HIP_MMVQ_N1_Q8_0=0 | lfm | tg,serve |  |  | HIP/RDNA3 one-column MMVQ: Q8_0 joins the 2-row path (and the 4-row conv path) (GGML_HIP_M |
| 65 | c36fd2c87 | env | LLAMA_SERVER_REASONING_CONTROL=1 | qwen,lfm | serve |  | web-UI requests only: measured with reasoning_control=true in the request | server: LLAMA_SERVER_REASONING_CONTROL=0 ignores the client reasoning_control flag (the we |

Env switches: name found as a string literal in non-comment code at HEAD (file:line in loo-plan.json `env_found`).
Revert check: `git merge-tree --write-tree --merge-base=<sha> HEAD <sha>^` (no worktree). A conflicting revert lists the later patches touching the conflicted files: those need a manual LOO port or a group revert.
