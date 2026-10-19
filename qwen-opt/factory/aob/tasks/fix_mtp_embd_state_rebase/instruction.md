# Qwen MTP server crashes after the rebase

Symptom: after the rebase onto v0.7.0 the Qwen MTP server with a draft vocabulary aborts on the first request
(an assertion about the batch state). Make MTP drafting work again; greedy output must match the pre-rebase MTP output
in the same mode.

Files to look at: `common/speculative.cpp`, `src/llama-batch.cpp`, `src/llama-context.cpp`.

Gate your whole change behind the env switch `GGML_HIP_AOB_T5` (1 = on, 0 = off, default off).

Local measurement: only `./factory verify <card> --dry-run` (prints the plan, runs nothing). Never launch GPU work yourself; the planner measures.
