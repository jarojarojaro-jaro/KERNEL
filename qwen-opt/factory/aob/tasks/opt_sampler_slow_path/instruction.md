# Clients see slower LFM than llama-bench suggests

Symptom: through the web UI and the omp tools LFM runs at ~254 t/s, while llama-bench suggests more.
Find where client requests lose throughput on the host side and fix it; generated text and tool calls must stay the same.

Files to look at: `common/sampling.cpp`, `common/sampling.h`, `tools/server/server-context.cpp`, `src/llama-sampler.cpp`.

Gate your whole change behind the env switch `GGML_HIP_AOB_T3` (1 = on, 0 = off, default off).

Local measurement: only `./factory verify <card> --dry-run` (prints the plan, runs nothing). Never launch GPU work yourself; the planner measures.
