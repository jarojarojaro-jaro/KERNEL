# Faster Q4_K/Q5_K prefill on gfx1100

Goal: speed up prompt processing (llama-bench `pp4096`) of Qwen3.8-27B Q4_K/Q5_K on the RX 7900 XTX (gfx1100).
Results must be bit-identical (logits of the prefill and test-backend-ops MUL_MAT / MUL_MAT_ID unchanged).

Files to look at: `ggml/src/ggml-cuda/mmq.cuh`, `ggml/src/ggml-cuda/mmq-vec-dot.cuh`, `ggml/src/ggml-cuda/vecdotq.cuh`.
Do not regress pp512 or LFM prefill.

Gate your whole change behind the env switch `GGML_HIP_AOB_T1` (1 = on, 0 = off, default off).

Local measurement: only `./factory verify <card> --dry-run` (prints the plan, runs nothing). Never launch GPU work yourself; the planner measures.
