---
typ: nvidia
tags: [nvidia, latki, wylaczniki]
aktualizacja: 2026-10-16
zrodlo: ~/qwen-opt/cloud/CUDA-AUDIT.md:13-18,99-172,248-284; ~/qwen-opt/cloud/PLAN-TESTOW.md:73-83; ~/KERNEL/product/research/09-chmura-3090.md:74-104; ~/KERNEL/product/research/09-chmura-5060ti.md:55,91-119; ~/KERNEL/product/research/09-chmura-3060.md:111-127
status: aktualne
---
# Które łatki działają na NVIDIA

**Na NVIDIA domyślnie działa ok. 35 z 70 łatek; kod tylko dla AMD (DPP, WMMA, buffer resource, PM4, kvq) jest za guardami albo bramką RDNA.**

Aktywne bez przełącznika runtime (tylko przebudowa): 0001/0002 (MMVQ 2–8 kolumn; wyłącza je `-DMMVQ_DISABLE_MULTI`), 0003 (cache q8_1), 0023 (clamp), 0043 (kolejność chunków K w FA MMA; na NVIDIA okazała się no-opem), 0045 (pre-pass GDN), 0033–0036 (lag/replay GDN przy spekulacji).

Zbiorczo: upstreamowy `GGML_CUDA_DISABLE_FUSION=1` wyłącza fuzje 0012–0017, 0019, 0024, 0027, 0028, 0038, 0049–0051, 0053, 0056, 0057 (ale też fuzje upstream). Pojedynczo działają na CUDA m.in. `GGML_HIP_MMVQ_PAIR`, `_NORM_FAST`, `_ARGMAX_FAST`, `_NORM_GATE`, `_GDN_CONV_AB`, `_Q8_IDS`, `_CONV_MUL`, `_MOE_DOWN_REDUCE`, `_NORM_ROUTER`, `_GATE_UP_Q8`, `_ATTN_PREP`, `_INPUT_BATCH` oraz przełączniki `LLAMA_*` hosta i samplera.

Bez efektu na NVIDIA (ścieżki RDNA): `GGML_HIP_INPROJ_CONV`, `_CONV_ROWS4`, `_MMVQ_N1_ROWS`, `_MMVQ_N1_Q8_0`, `_KVQ_Q8`, `_KVQ_FWHT`, `_MMQ_EPI`, `_PM4`.

Łatki, które mogły zmienić numerykę na CUDA (PLAN-TESTOW): 0013, 0043, 0001/0002, 0023, 0018. Stąd w harnessie tryb A2s („fork-safe”): wszystkie 31 przełączników = 0.

**Wynik kampanii (2026-10-16):** greedy różni się od upstreamu przez **0001/0002** (LFM: build z `-DMMVQ_DISABLE_MULTI` = md5 upstream) i **0013** (Qwen); 0043 okazała się na NVIDIA no-opem (`nbatch_K2 = 128 = DKQ/2` w tabelach Ampere+). KLD fork vs upstream na RTX 3060 na poziomie szumu. Przełączniki per arch:
- szkodzą na NVIDIA: `GGML_HIP_GATE_UP_Q8` (wszystkie karty), `GGML_HIP_Q8_IDS` (sm_120);
- pomagają: `CONV_MUL`, `NORM_ROUTER`, `ATTN_PREP`, `MOE_DOWN_REDUCE`, `NORM_FAST`, `LLAMA_ASYNC_INPUTS` (po ok. 1–2% na LFM);
- największy zysk w serwerze to sampler (`LLAMA_SAMPLER_FAST_TOPK`/`_PENALTIES`: LFM 165.5 → 207.7 t/s na 5060 Ti), niezależny od GPU;
- nowy `GGML_CUDA_MMVQ_N1_ROWS=2` tylko na sm_86. Wyłączenie grafów CUDA szkodzi (−6.9% LFM na 3090).

## Powiązane
- [[nvidia/_hub|NVIDIA]]
- [[cuda-compat]]
- [[wylaczniki-env]]
- [[nvidia-wyniki-2026-10-16]]
- [[klasyfikacja-latek]]
- [[lekcja-md5-wzgledem-upstreamu]]
- [[raport-09-chmura-5060ti]]
