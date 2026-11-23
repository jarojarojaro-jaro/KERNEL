---
typ: model
tags: [modele, lfm, uncensored]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/qwen-opt/research/lfm-decode-round4.md:14,129-133; ~/KERNEL/qwen-opt/STATUS-NEXT.md:13; ~/KERNEL/qwen-opt/run-llm.sh:11; ~/KERNEL/qwen-opt/README.md:56; ~/KERNEL/qwen-opt/NOTES.md:374-375; ~/KERNEL/product/research/16g-lfm-moe-pasmo.md:88,94-95; ~/KERNEL/product/research/21e-kv-miedzy-modelami.md:105-113
status: aktualne
model: lfm2-5-uncensored
rozmiar: 24B-A2B
kwant: AD-Q5_K_M
karty: rx-7900-xtx
wyniki:
  - lfm2-5-uncensored | rx-7900-xtx | 267.3 t/s | dekod; KV q8_0, łatka 0064 | 2026-10-15
  - lfm2-5-uncensored | rx-7900-xtx | 6291 t/s | prefill pp4096 | 2026-10-15
  - lfm2-5-uncensored | rx-7900-xtx | 268.27 t/s | dekod llama-bench; GGML_HIP_MOE_GU_BLOCK | 2026-10-18
---
# LFM2.5-24B-A2B-Uncensored (AtomicChat, AD-Q5_K_M)

**Abliterowany LFM2.5 od AtomicChat; ma więcej tensorów Q8_0, dlatego dostał własną łatkę MMVQ (0064) i działa z 267.3 t/s.**

- Plik: `~/models/lfm/LFM2.5-24B-A2B-Uncensored-AD-Q5_K_M.gguf` (16.10 GiB), `hf download AtomicChat/LFM2.5-24B-A2B-Uncensored-GGUF …` (sha256 w README).
- Mieszanka tensorów (round 4 §6): shortconv in_proj/out_proj, atencja q/k/v/o, gęste FFN i `token_embd` w Q8_0 (w zwykłym LFM: Q5_K, v/down/głowica Q6_K); eksperci: 33 warstwy Q5_K, 5 warstw Q6_K.
- Łatka 0064 (Q8_0 w ścieżce 2 wierszy MMVQ n=1): 3.933 → 3.706 ms/token (llama-bench, 3 rundy).
- Wyniki: soak po PM4 ~264 t/s; pomiar finalny 2026-10-15: **267.3 t/s**, 3.74 ms/krok, pp4096 6291, tg128 264.3 (KV q8_0).
- Uruchomienie: `run-llm.sh lfm-uncensored` (te same ustawienia co LFM).

16g (2026-10-18): `GGML_HIP_MOE_GU_BLOCK` obejmuje 33 warstwy z gate/up Q5_K (5 warstw Q6_K stara droga); llama-bench 264.60 → 268.27 t/s (+1.39%), hash logitów `f74300e3142a5535` bez zmian ([[2026-10-18-lfm-moe-pasmo]]).

Analiza wag (21e, 2026-10-19): LFM2.5 z ablacją kierunku per warstwa w warstwach 14–39, skala 1.75; warstwy 0–13 nieruszone – [[uncensored-ablacja-kierunku]].

<!-- TABELE:START -->
## Wyniki z notatek (4)

Najlepszy wynik na metrykę z pól `wynik` notatek testów (tools/tabele.py, 2026-11-23); pełna tabela: [[najlepsze-wyniki]].

| karta | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod | **267.3 t/s** | amd-opt | 2026-10-15 | [[rx-7900-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod llama-bench | **268.27 t/s** | GGML_HIP_MOE_GU_BLOCK | 2026-10-18 | [[lfm2-5-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill pp4096 | **6291 t/s** |  | 2026-10-15 | [[lfm2-5-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep T=1 | **267.3 t/s** | AD-Q5_K_M, KV q8_0 | 2026-10-15 | [[stan-2026-10-15]] |
<!-- TABELE:END -->

## Powiązane
- [[modele/_hub|Modele]]
- [[lfm2-5-24b-a2b]]
- [[mmvq-n1-wiersze]]
- [[stan-2026-10-15]]
- [[kwanty-gguf]]
