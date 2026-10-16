---
typ: nvidia
tags: [nvidia, latki, wylaczniki]
aktualizacja: 2026-10-16
zrodlo: ~/qwen-opt/cloud/CUDA-AUDIT.md:13-18,99-172,248-284; ~/qwen-opt/cloud/PLAN-TESTOW.md:73-83
status: aktualne
---
# Które łatki działają na NVIDIA

**Na NVIDIA domyślnie działa ok. 35 z 70 łatek; kod tylko dla AMD (DPP, WMMA, buffer resource, PM4, kvq) jest za guardami albo bramką RDNA.**

Aktywne bez przełącznika runtime (tylko przebudowa): 0001/0002 (MMVQ 2–8 kolumn; wyłącza je `-DMMVQ_DISABLE_MULTI`), 0003 (cache q8_1), 0023 (clamp), 0043 (kolejność chunków K w FA MMA: wynik bitowo różny od upstream na NVIDIA), 0045 (pre-pass GDN), 0033–0036 (lag/replay GDN przy spekulacji).

Zbiorczo: upstreamowy `GGML_CUDA_DISABLE_FUSION=1` wyłącza fuzje 0012–0017, 0019, 0024, 0027, 0028, 0038, 0049–0051, 0053, 0056, 0057 (ale też fuzje upstream). Pojedynczo działają na CUDA m.in. `GGML_HIP_MMVQ_PAIR`, `_NORM_FAST`, `_ARGMAX_FAST`, `_NORM_GATE`, `_GDN_CONV_AB`, `_Q8_IDS`, `_CONV_MUL`, `_MOE_DOWN_REDUCE`, `_NORM_ROUTER`, `_GATE_UP_Q8`, `_ATTN_PREP`, `_INPUT_BATCH` oraz przełączniki `LLAMA_*` hosta i samplera.

Bez efektu na NVIDIA (ścieżki RDNA): `GGML_HIP_INPROJ_CONV`, `_CONV_ROWS4`, `_MMVQ_N1_ROWS`, `_MMVQ_N1_Q8_0`, `_KVQ_Q8`, `_KVQ_FWHT`, `_MMQ_EPI`, `_PM4`.

Łatki, które mogą zmienić numerykę na CUDA (PLAN-TESTOW): 0013 (GDN, KLD 0.0067 na AMD), 0043, 0001/0002 (inny podział bloków na NVIDIA, niesprawdzony), 0023, 0018. Stąd w harnessie tryb A2s („fork-safe”): wszystkie 31 przełączników = 0, zostają tylko łatki bez przełącznika.

## Powiązane
- [[nvidia/_hub|NVIDIA]]
- [[cuda-compat]]
- [[wylaczniki-env]]
- [[nvidia-wyniki-2026-10-16]]
- [[klasyfikacja-latek]]
