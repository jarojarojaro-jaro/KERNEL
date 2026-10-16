---
typ: latka
tags: [latki, wylaczniki, env]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/patch-manifest.json (pole env_switch, 0001–0070); ~/KERNEL/qwen-opt/NOTES.md:345-383; ~/KERNEL/qwen-opt/research/round6/gdn-bitwise.md:13-16
status: aktualne
---
# Wyłączniki env łatek

**Każdy przełącznik jest domyślnie włączony; `=0` przywraca ścieżkę sprzed łatki w tej samej binarce.**

| zmienna | łatka | co wyłącza |
|---|---|---|
| `GGML_HIP_MMVQ_PAIR` | 0024 | para MMVQ jedną siatką |
| `GGML_HIP_NORM_FAST` | 0025 | rms_norm·mul z DPP |
| `GGML_HIP_ARGMAX_FAST` | 0026 | argmax z DPP |
| `GGML_HIP_NORM_GATE` | 0027 | bramkowana norma GDN |
| `GGML_HIP_GDN_CONV_AB` | 0028 | SSM_CONV + alpha/beta |
| `LLAMA_ASYNC_INPUTS` | 0029 | asynchroniczne wejścia grafu |
| `LLAMA_MTP_CHAIN_SCHED` | 0030 | osobny scheduler draftu MTP |
| `LLAMA_SAMPLER_FAST_TOPK`, `LLAMA_SPEC_LAZY_SAVE` | 0031 | szybkie top-k, leniwa kopia samplera |
| `LLAMA_GDN_REPLAY` (manifest: także `GGML_HIP_GDN_REPLAY`) | 0033 | lag/replay GDN (gasi też 0034–0036, 0038) |
| `LLAMA_CONV_LAG` | 0038 | historia conv z opóźnieniem |
| `LLAMA_KV_MASK_FAST`, `LLAMA_KV_SEQ_RM_SCAN` | 0047 | koszty hosta pętli spekulacji |
| `LLAMA_SAMPLER_FAST_PENALTIES` | 0048 | top-k za samplerem kar |
| `GGML_HIP_Q8_IDS` | 0049 | q8_1 z normy dla ekspertów |
| `GGML_HIP_CONV_MUL` | 0050 | mnożenia shortconv w SSM_CONV |
| `GGML_HIP_MOE_DOWN_REDUCE` | 0051 | down + ważenie + residual |
| `GGML_HIP_MMVQ_N1_ROWS` | 0052 | 2 wiersze/blok n=1 |
| `GGML_HIP_NORM_ROUTER` | 0053 | norma + router + top-k |
| `GGML_HIP_INPROJ_CONV` | 0054 | conv w in_proj |
| `GGML_HIP_KVQ_Q8` | 0055 | kvq dla KV q8_0 |
| `GGML_HIP_GATE_UP_Q8` | 0056 | q8_1 z gate/up |
| `GGML_HIP_ATTN_PREP` | 0057 | wejście atencji jednym kernelem |
| `GGML_HIP_KVQ_FWHT` | 0058 | FWHT w combine |
| `GGML_HIP_INPUT_BATCH` | 0059 | zbiorczy upload wejść |
| `GGML_HIP_PM4` (`GGML_HIP_PM4_DEBUG=1/2/3` diagnostyka) | 0060, 0061 | replay PM4 |
| `GGML_HIP_CONV_ROWS4` | 0062 | in_proj+conv 4 wiersze/blok |
| `GGML_HIP_MMVQ_N1_Q8_0` | 0064 | Q8_0 w ścieżce 2 wierszy |
| `LLAMA_SERVER_REASONING_CONTROL` | 0065 | ignorowanie `reasoning_control` |
| `LLAMA_SAMPLER_FAST_RBUDGET` / `_NPROBS` / `_LOGIT_BIAS` / `_GRAMMAR` | 0066–0069 | szybkie top-k w tych przypadkach |
| `GGML_HIP_MMQ_EPI` | 0070 | epilog MMQ VOPD |

Poza `amd-opt` (gałąź `opt-gdn6`): `GGML_HIP_GDN_FAST`, `GGML_HIP_GDN_B128`. CLI zamiast env: 0004 `--spec-draft-vocab(-n)`, 0032 `--spec-draft-head-type` / `--spec-mtp-type`; opt-in: 0039 `--spec-draft-adaptive`, 0046 `--spec-mtp-window`. Uwaga: przełączniki `GGML_HIP_*` czyta też build CUDA.

## Powiązane
- [[latki/_hub|Łatki]]
- [[wylacznik-w-kazdej-latce]]
- [[loo]]
- [[patch-manifest]]
- [[run-llm-sh]]
