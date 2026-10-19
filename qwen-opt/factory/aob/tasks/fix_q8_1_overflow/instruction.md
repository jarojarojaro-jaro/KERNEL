# NaN / garbage after a large activation

Symptom: on some long prompts Qwen starts generating NaN or garbage right after one very large activation.
Find and fix the cause without changing output on normal inputs.

Files to look at: `ggml/src/ggml-cuda/quantize.cu`, `ggml/src/ggml-cuda/mmq.cuh`, `ggml/src/ggml-cuda/fattn-common.cuh`.

Gate your whole change behind the env switch `GGML_HIP_AOB_T2` (1 = on, 0 = off, default off).

Local measurement: only `./factory verify <card> --dry-run` (prints the plan, runs nothing). Never launch GPU work yourself; the planner measures.
